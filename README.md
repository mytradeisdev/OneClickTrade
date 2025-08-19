
# UnoClick — Trade Approvals (PWA + FastAPI + Kite)

UnoClick sends **trade recommendations** to your phone (via FCM). If you tap **Approve**, it executes the legs on **Zerodha Kite** and arms **OCO GTT** (−12% / +25%) for BUY legs.

## Structure
```
unoclick-trader/
  client/        # PWA — host on Netlify/Cloudflare Pages
  server/        # FastAPI — deploy on Render/Railway/Cloud Run
  README.md
```

## Quick Start (browser-only)
1) **Create Firebase project** → web app config + Web Push (VAPID) key + Service Account JSON.
2) Edit `client/app.js` + `client/firebase-messaging-sw.js` with your Firebase config.
3) Deploy `client/` to Netlify (Publish directory = client). HTTPS required.
4) Deploy `server/`:
   ```bash
   cd server
   pip install -r requirements.txt
   export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/firebase-service-account.json
   export JWT_SECRET="change_me_to_long_random"
   export PUBLIC_BASE_URL="https://your-unoclick-server.example"
   export KITE_API_KEY="your_kite_key"
   export KITE_API_SECRET="your_kite_secret"
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
5) Open `https://your-unoclick-server.example/admin` → paste **KITE_ACCESS_TOKEN** (daily).
6) On your phone (Chrome) open your client URL → **Allow notifications** → **Add to Home Screen**. Copy the **FCM token**.

## Send a recommendation
```bash
curl -X POST "$PUBLIC_BASE_URL/notify/alert"   -H 'Content-Type: application/json'   -d '{
    "token":"<device_fcm_token>",
    "title":"Rotate 50% PREMEXPLN → RAJOOENG",
    "body":"SELL 3 PREMEXPLN, BUY 12 RAJOOENG. Approve?",
    "rec_id":"demo-001",
    "orders":[
      {"side":"SELL","symbol":"PREMEXPLN","qty":3},
      {"side":"BUY","symbol":"RAJOOENG","qty":12}
    ]
  }'
```
Tap **Approve** on the notification → server verifies the signed JWT and places orders (SELL first, then BUY). BUY legs get **OCO GTT** armed based on current LTP.

## Notes
- Tokens expire daily; paste new **KITE_ACCESS_TOKEN** in `/admin` each day.
- Use HTTPS and keep secrets safe.
- To restrict devices, put allowed FCM tokens into `server/allowed_tokens.json`.
