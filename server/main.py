
# server/main.py — UnoClick MVP: Push → Approve → Execute via Kite
import os, time, json, hashlib
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import jwt
from jwt import PyJWTError
from kiteconnect import KiteConnect
import firebase_admin
from firebase_admin import credentials, messaging






# --- Config via env ---
JWT_SECRET = os.getenv('JWT_SECRET', 'change_me')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', 'http://127.0.0.1:8000')
KITE_API_KEY = os.getenv('KITE_API_KEY', '')
KITE_API_SECRET = os.getenv('KITE_API_SECRET', '')
KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', '')  # can be set via /admin
EXCHANGE = os.getenv('EXCHANGE', 'NSE')
PRODUCT = os.getenv('PRODUCT', 'CNC')
STOP_PCT = float(os.getenv('STOP_PCT', '0.12'))
TARGET_PCT = float(os.getenv('TARGET_PCT', '0.25'))

# Optional allowlist for device tokens
ALLOWED_TOKENS_FILE = os.getenv('ALLOWED_TOKENS_FILE', 'server/allowed_tokens.json')
PORTFOLIO_FILE = os.getenv('PORTFOLIO_FILE', 'server/portfolio.json')
LOG_FILE = os.getenv('LOG_FILE', 'server/logs.jsonl')

# Firebase Admin (service account via GOOGLE_APPLICATION_CREDENTIALS)
# Firebase Admin (service account JSON loaded from env)
if not firebase_admin._apps:
    firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if firebase_json:
        cred = credentials.Certificate(json.loads(firebase_json))
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to GOOGLE_APPLICATION_CREDENTIALS if set by the platform
        firebase_admin.initialize_app()

app = FastAPI(title="UnoClick Backend")

# add this right after:
@app.get("/")
def root():
    return {"status": "ok", "service": "UnoClick", "routes": ["/admin", "/portfolio", "/logs", "/notify/test", "/notify/alert", "/approve", "/docs"]}

def log_event(ev: dict):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')
    except Exception:
        pass

def load_json(path: str, default):
    try:
        with open(path, 'r') as f: return json.load(f)
    except Exception:
        return default

# Bootstrap portfolio file if missing
if not os.path.exists(PORTFOLIO_FILE):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump([
            {"symbol":"PREMEXPLN","qty":7,"entry":532.00},
            {"symbol":"RPPINFRA","qty":24,"entry":109.98},
            {"symbol":"GNA","qty":8,"entry":298.10},
            {"symbol":"SJS","qty":1,"entry":1176.40}
        ], f, indent=2)

class OrderLeg(BaseModel):
    side: str  # BUY or SELL
    symbol: str
    qty: int

class AlertBody(BaseModel):
    token: str
    title: Optional[str] = None
    body: Optional[str] = None
    rec_id: Optional[str] = None
    orders: List[OrderLeg] = []

class TestBody(BaseModel):
    token: str

@app.get('/admin', response_class=HTMLResponse)
async def admin_form():
    html = f'''<html><body style="font-family:system-ui;max-width:560px;margin:40px auto;">
    <h2>UnoClick Admin</h2>
    <form method="post" action="/admin/token">
      <label>KITE Access Token (daily)</label><br/>
      <input type="text" name="access_token" style="width:100%;padding:.6rem" /><br/><br/>
      <button type="submit" style="padding:.6rem 1rem">Save</button>
    </form>
    <p>Current key set: <b>{'YES' if bool(os.getenv('KITE_ACCESS_TOKEN', KITE_ACCESS_TOKEN)) else 'NO'}</b></p>
    <p><a href="/portfolio">View portfolio</a> · <a href="/logs">Download logs</a></p>
    </body></html>'''
    return HTMLResponse(html)

@app.post('/admin/token')
async def admin_set_token(access_token: str = Form(...)):
    global KITE_ACCESS_TOKEN
    KITE_ACCESS_TOKEN = access_token
    os.environ['KITE_ACCESS_TOKEN'] = access_token
    log_event({"ts": time.time(), "evt": "admin_token_set"})
    return {"ok": True}

def kite_client():
    kite = KiteConnect(api_key=KITE_API_KEY)
    tok = os.getenv('KITE_ACCESS_TOKEN', KITE_ACCESS_TOKEN)
    if not tok:
        raise HTTPException(403, 'KITE_ACCESS_TOKEN missing; set via /admin')
    kite.set_access_token(tok)
    return kite

def place_sequence_and_gtt(legs: List[OrderLeg]):
    kite = kite_client()
    sell_legs = [l for l in legs if l.side.upper() == 'SELL']
    buy_legs  = [l for l in legs if l.side.upper() == 'BUY']
    results = []

    # SELL first
    for l in sell_legs:
        oid = kite.place_order(variety='regular', exchange=EXCHANGE, tradingsymbol=l.symbol,
                               transaction_type='SELL', quantity=int(l.qty),
                               order_type=KiteConnect.ORDER_TYPE_MARKET, product=KiteConnect.PRODUCT_CNC,
                               validity=KiteConnect.VALIDITY_DAY)
        results.append({"leg": l.dict(), "order_id": oid})

    # BUY then arm OCO GTT
    for l in buy_legs:
        oid = kite.place_order(variety='regular', exchange=EXCHANGE, tradingsymbol=l.symbol,
                               transaction_type='BUY', quantity=int(l.qty),
                               order_type=KiteConnect.ORDER_TYPE_MARKET, product=KiteConnect.PRODUCT_CNC,
                               validity=KiteConnect.VALIDITY_DAY)
        results.append({"leg": l.dict(), "order_id": oid})

        ltp = kite.ltp([f"{EXCHANGE}:{l.symbol}"])[f"{EXCHANGE}:{l.symbol}"]["last_price"]
        stop_trig   = round(float(ltp) * (1 - STOP_PCT), 2)
        target_trig = round(float(ltp) * (1 + TARGET_PCT), 2)
        orders = [
            {"exchange": EXCHANGE, "tradingsymbol": l.symbol, "transaction_type": KiteConnect.TRANSACTION_TYPE_SELL,
             "quantity": int(l.qty), "order_type": KiteConnect.ORDER_TYPE_LIMIT, "product": PRODUCT, "price": stop_trig},
            {"exchange": EXCHANGE, "tradingsymbol": l.symbol, "transaction_type": KiteConnect.TRANSACTION_TYPE_SELL,
             "quantity": int(l.qty), "order_type": KiteConnect.ORDER_TYPE_LIMIT, "product": PRODUCT, "price": target_trig}
        ]
        gid = kite.place_gtt(trigger_type=KiteConnect.GTT_TYPE_OCO, tradingsymbol=l.symbol, exchange=EXCHANGE,
                             trigger_values=[stop_trig, target_trig], last_price=float(ltp), orders=orders)
        results.append({"leg": l.dict(), "gtt_id": gid, "stop": stop_trig, "target": target_trig})
    return results
# --- add this route after app init ---


@app.get("/kite/login")
def kite_login():
    # quick redirect to Zerodha login for your API key
    return RedirectResponse(
        url=f"https://kite.trade/connect/login?v=3&api_key={KITE_API_KEY}"
    )


@app.get("/kite/callback")
def kite_callback(request: Request):
    """
    Zerodha redirects here with ?status=success&request_token=xxxx
    We exchange it for an access_token and store it.
    """
    params = dict(request.query_params)
    if params.get("status") != "success" or "request_token" not in params:
        raise HTTPException(400, f"Bad callback: {params}")

    request_token = params["request_token"]
    kite = KiteConnect(api_key=KITE_API_KEY)
    try:
        session = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
        access_token = session["access_token"]
    except Exception as e:
        raise HTTPException(500, f"Token exchange failed: {e}")

    # Persist it in memory/env (and logs)
    global KITE_ACCESS_TOKEN
    KITE_ACCESS_TOKEN = access_token
    os.environ["KITE_ACCESS_TOKEN"] = access_token
    log_event({"ts": time.time(), "evt": "kite_access_token_set"})

    # optional: quick test call (profile) to confirm it works
    kite.set_access_token(access_token)
    try:
        _ = kite.profile()
    except Exception as e:
        log_event({"ts": time.time(), "evt": "kite_profile_check_fail", "err": str(e)})

    # Redirect to a simple success page (or /admin)
    return RedirectResponse(url="/admin")

@app.post('/notify/test')
async def notify_test(b: TestBody):
    note = messaging.Notification(title='UnoClick Test', body='If you see this, push works!')
    msg = messaging.Message(notification=note, token=b.token)
    rid = messaging.send(msg)
    log_event({"ts": time.time(), "evt": "test_push", "rid": rid})
    return {"id": rid}

@app.get('/portfolio')
async def get_portfolio():
    return load_json(PORTFOLIO_FILE, [])

@app.get('/logs')
async def get_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            return HTMLResponse('<pre>'+f.read()+'</pre>')
    except Exception:
        return HTMLResponse('<pre>(no logs)</pre>')

@app.post('/notify/alert')
async def notify_alert(request: Request):
    b = await request.json()
    token = b.get("token")
    title = b.get("title") or "Trade Recommendation"
    body  = b.get("body") or "Approve to execute via Kite."
    orders = b.get("orders", [])
    rec_id = b.get("rec_id") or str(int(time.time()))

    allow = load_json(ALLOWED_TOKENS_FILE, [])
    if allow and token not in allow:
        raise HTTPException(403, 'device token not allowed')

    legs_hash = hashlib.sha256(json.dumps(orders, sort_keys=True).encode()).hexdigest()[:16]
    payload = {"rec_id": rec_id, "legs_hash": legs_hash, "legs": orders, "exp": int(time.time()) + 600}
    signed = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    approve_url = f"{PUBLIC_BASE_URL}/approve?token={signed}"

    note = messaging.Notification(title=title, body=body)
    msg = messaging.Message(notification=note, token=token, data={"approveUrl": approve_url})
    rid = messaging.send(msg)
    log_event({"ts": time.time(), "evt": "alert_push", "rec_id": rec_id, "rid": rid, "legs": orders})
    return {"id": rid, "approve_url": approve_url}

@app.get('/approve')
async def approve(request: Request):
    tok = request.query_params.get('token')
    if not tok: raise HTTPException(400, 'missing token')
    try:
        payload = jwt.decode(tok, JWT_SECRET, algorithms=['HS256'])
    except PyJWTError as e:
        raise HTTPException(401, f'invalid token: {e}')

    legs = payload.get('legs', [])
    if not legs: raise HTTPException(400, 'no legs provided')

    # validate and coerce into OrderLeg
    parsed = [OrderLeg(**l) for l in legs]
    try:
        results = place_sequence_and_gtt(parsed)
        log_event({"ts": time.time(), "evt": "approved_executed", "rec_id": payload.get('rec_id'), "results": results})
        return JSONResponse({"status": "ok", "rec_id": payload.get('rec_id'), "results": results})
    except Exception as e:
        log_event({"ts": time.time(), "evt": "approved_failed", "rec_id": payload.get('rec_id'), "error": str(e)})
        raise HTTPException(500, f'Order failed: {e}')
