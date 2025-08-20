import json, os, time
from typing import List
from .config import LOG_FILE, PORTFOLIO_FILE, DEVICES_FILE

def log_event(ev: dict) -> None:
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')
    except Exception:
        pass

def load_json(path: str, default):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return default

def ensure_portfolio_seed():
    if not os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump([
                {"symbol":"PREMEXPLN","qty":7,"entry":532.00},
                {"symbol":"RPPINFRA","qty":24,"entry":109.98},
                {"symbol":"GNA","qty":8,"entry":298.10},
                {"symbol":"SJS","qty":1,"entry":1176.40}
            ], f, indent=2)

# Device registry
def load_devices() -> List[str]:
    tokens = load_json(DEVICES_FILE, [])
    return tokens if isinstance(tokens, list) else []

def save_devices(tokens: List[str]) -> None:
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
    except Exception:
        pass
