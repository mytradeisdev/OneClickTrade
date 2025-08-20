import hmac, hashlib, os
from kiteconnect import KiteConnect
from .config import (
    KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN,
    EXCHANGE, PRODUCT, STOP_PCT, TARGET_PCT
)
from fastapi import HTTPException
from .models import OrderLeg

def kite_client() -> KiteConnect:
    kite = KiteConnect(api_key=KITE_API_KEY)
    tok = os.getenv('KITE_ACCESS_TOKEN', KITE_ACCESS_TOKEN)
    if not tok:
        raise HTTPException(403, 'KITE_ACCESS_TOKEN missing; set via /admin or /kite/callback')
    kite.set_access_token(tok)
    return kite

def place_sequence_and_gtt(legs):
    kite = kite_client()
    sell_legs = [l for l in legs if l.side.upper() == 'SELL']
    buy_legs  = [l for l in legs if l.side.upper() == 'BUY']
    results = []

    # SELL first
    for l in sell_legs:
        oid = kite.place_order(
            variety='regular', exchange=EXCHANGE, tradingsymbol=l.symbol,
            transaction_type='SELL', quantity=int(l.qty),
            order_type=KiteConnect.ORDER_TYPE_MARKET, product=KiteConnect.PRODUCT_CNC,
            validity=KiteConnect.VALIDITY_DAY
        )
        results.append({"leg": l.dict(), "order_id": oid})

    # BUY then OCO GTT
    for l in buy_legs:
        oid = kite.place_order(
            variety='regular', exchange=EXCHANGE, tradingsymbol=l.symbol,
            transaction_type='BUY', quantity=int(l.qty),
            order_type=KiteConnect.ORDER_TYPE_MARKET, product=KiteConnect.PRODUCT_CNC,
            validity=KiteConnect.VALIDITY_DAY
        )
        results.append({"leg": l.dict(), "order_id": oid})

        ltp = kite.ltp([f"{EXCHANGE}:{l.symbol}"])[f"{EXCHANGE}:{l.symbol}"]["last_price"]
        stop_trig   = round(float(ltp) * (1 - STOP_PCT), 2)
        target_trig = round(float(ltp) * (1 + TARGET_PCT), 2)
        orders = [
            {
                "exchange": EXCHANGE, "tradingsymbol": l.symbol,
                "transaction_type": KiteConnect.TRANSACTION_TYPE_SELL,
                "quantity": int(l.qty), "order_type": KiteConnect.ORDER_TYPE_LIMIT,
                "product": PRODUCT, "price": stop_trig
            },
            {
                "exchange": EXCHANGE, "tradingsymbol": l.symbol,
                "transaction_type": KiteConnect.TRANSACTION_TYPE_SELL,
                "quantity": int(l.qty), "order_type": KiteConnect.ORDER_TYPE_LIMIT,
                "product": PRODUCT, "price": target_trig
            }
        ]
        gid = kite.place_gtt(
            trigger_type=KiteConnect.GTT_TYPE_OCO, tradingsymbol=l.symbol, exchange=EXCHANGE,
            trigger_values=[stop_trig, target_trig], last_price=float(ltp), orders=orders
        )
        results.append({"leg": l.dict(), "gtt_id": gid, "stop": stop_trig, "target": target_trig})

    return results

def verify_kite_signature(raw_body: bytes, header_value: str, api_secret: str = KITE_API_SECRET) -> bool:
    if not header_value:
        return False
    digest = hmac.new(api_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header_value)
