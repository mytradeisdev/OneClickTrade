import json, base64
import firebase_admin
from firebase_admin import credentials, messaging
from .config import FIREBASE_SERVICE_ACCOUNT_JSON

def _load_service_account_dict() -> dict:
    raw = FIREBASE_SERVICE_ACCOUNT_JSON
    if not raw:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not set")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)

def init_firebase():
    if not firebase_admin._apps:
        sa = _load_service_account_dict()
        proj = sa.get("project_id")
        if not proj:
            raise RuntimeError("Service account JSON missing project_id")
        cred = credentials.Certificate(sa)
        firebase_admin.initialize_app(cred, {"projectId": proj})
        print(f"[Firebase] Initialized for project_id={proj}")

# Make messaging importable for callers
__all__ = ["init_firebase", "messaging"]
