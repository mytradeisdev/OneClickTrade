import os

JWT_SECRET        = os.getenv('JWT_SECRET', 'change_me')
PUBLIC_BASE_URL   = os.getenv('PUBLIC_BASE_URL', 'http://127.0.0.1:8000')

KITE_API_KEY      = os.getenv('KITE_API_KEY', '')
KITE_API_SECRET   = os.getenv('KITE_API_SECRET', '')
KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', '')  # mutated by /admin or /kite/callback

EXCHANGE          = os.getenv('EXCHANGE', 'NSE')
PRODUCT           = os.getenv('PRODUCT', 'CNC')
STOP_PCT          = float(os.getenv('STOP_PCT', '0.12'))
TARGET_PCT        = float(os.getenv('TARGET_PCT', '0.25'))

ALLOWED_TOKENS_FILE = os.getenv('ALLOWED_TOKENS_FILE', 'server/allowed_tokens.json')
PORTFOLIO_FILE      = os.getenv('PORTFOLIO_FILE', 'server/portfolio.json')
LOG_FILE            = os.getenv('LOG_FILE', 'server/logs.jsonl')
DEVICES_FILE        = os.getenv('DEVICES_FILE', 'server/devices.json')

FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
