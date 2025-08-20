from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def root():
    return {
        "status": "ok",
        "service": "UnoClick",
        "routes": [
            "/admin", "/portfolio", "/logs",
            "/devices/register", "/devices/list",
            "/notify/test", "/notify/alert", "/approve",
            "/kite/login", "/kite/callback", "/kite/postback",
            "/docs"
        ]
    }
