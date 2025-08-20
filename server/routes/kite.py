import time, json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from ..config import KITE_API_KEY, KITE_API_SECRET
from ..kite_utils import verify_kite_signature
from ..firebase import messaging
from ..storage import log_event, load_devices
from ..config import EXCHANGE

router = APIRouter()

@router.get("/kite/login")
def kite_login():
    return RedirectResponse(url=f"https://kite.trade/connect/login?v=3&api_key={KITE_API_KEY}")

@router.get("/kite/callback")
def kite_callback(request: Request):
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

    # Persist to process env (instance lifetime)
    import os
    os.environ["KITE_ACCESS_TOKEN"] = access_token
    log_event({"ts": time.time(), "evt": "kite_access_token_set"})
    kite.set_access_token(access_token)

    try:
        _ = kite.profile()
    except Exception as e:
        log_event({"ts": time.time(), "evt": "kite_profile_check_fail", "err": str(e)})

    return RedirectResponse(url="/admin")

@router.post("/kite/postback")
async def kite_postback(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Kite-Checksum") or request.headers.get("X-Kite-Signature") or ""
    if not verify_kite_signature(raw, sig):
        raise HTTPException(401, "Invalid postback signature")

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    order_id   = data.get("order_id") or data.get("order_id_str") or "NA"
    status     = data.get("status") or data.get("order_status") or "NA"
    tradingsym = data.get("tradingsymbol") or data.get("instrument_token") or "NA"
    qty        = data.get("quantity") or data.get("filled_quantity") or data.get("pending_quantity") or 0
    price      = data.get("average_price") or data.get("price") or 0
    ts         = data.get("exchange_timestamp") or data.get("order_timestamp") or ""

    title = f"Order {status}: {tradingsym}"
    body  = f"Qty {qty} @ {price} | {order_id}"

    tokens = load_devices()
    sent, failed = 0, 0
    for t in tokens:
        try:
            note = messaging.Notification(title=title, body=body)
            msg = messaging.Message(notification=note, token=t, data={
                "order_id": str(order_id), "status": str(status),
                "symbol": str(tradingsym), "qty": str(qty),
                "price": str(price), "ts": str(ts),
            })
            messaging.send(msg)
            sent += 1
        except Exception as e:
            failed += 1
            log_event({"ts": time.time(), "evt": "postback_push_fail", "token": t, "error": str(e)})

    log_event({"ts": time.time(), "evt": "kite_postback", "status": status, "symbol": tradingsym,
               "qty": qty, "price": price, "sent": sent, "failed": failed, "raw": data})
    return {"ok": True, "sent": sent, "failed": failed}
