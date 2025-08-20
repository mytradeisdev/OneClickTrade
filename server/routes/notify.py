import time, json, hashlib, jwt
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from jwt import PyJWTError
from ..firebase import messaging
from ..config import JWT_SECRET, PUBLIC_BASE_URL, ALLOWED_TOKENS_FILE, PORTFOLIO_FILE, LOG_FILE
from ..storage import load_json, log_event
from ..models import TestBody, OrderLeg, AlertBody
from ..kite_utils import place_sequence_and_gtt

router = APIRouter()

@router.post('/notify/test')
async def notify_test(b: TestBody):
    note = messaging.Notification(title='UnoClick Test', body='If you see this, push works!')
    msg = messaging.Message(notification=note, token=b.token)
    rid = messaging.send(msg)
    log_event({"ts": time.time(), "evt": "test_push", "rid": rid})
    return {"id": rid}

@router.get('/portfolio')
async def get_portfolio():
    return load_json(PORTFOLIO_FILE, [])

@router.get('/logs')
async def get_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            return HTMLResponse('<pre>'+f.read()+'</pre>')
    except Exception:
        return HTMLResponse('<pre>(no logs)</pre>')

@router.post('/notify/alert')
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

@router.get('/approve')
async def approve(request: Request):
    tok = request.query_params.get('token')
    if not tok:
        raise HTTPException(400, 'missing token')
    try:
        payload = jwt.decode(tok, JWT_SECRET, algorithms=['HS256'])
    except PyJWTError as e:
        raise HTTPException(401, f'invalid token: {e}')

    legs = payload.get('legs', [])
    if not legs:
        raise HTTPException(400, 'no legs provided')

    parsed = [OrderLeg(**l) for l in legs]
    try:
        results = place_sequence_and_gtt(parsed)
        log_event({"ts": time.time(), "evt": "approved_executed", "rec_id": payload.get('rec_id'), "results": results})
        return JSONResponse({"status": "ok", "rec_id": payload.get('rec_id'), "results": results})
    except Exception as e:
        log_event({"ts": time.time(), "evt": "approved_failed", "rec_id": payload.get('rec_id'), "error": str(e)})
        raise HTTPException(500, f'Order failed: {e}')
