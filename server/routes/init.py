from fastapi import APIRouter
from .health import router as health_router
from .admin import router as admin_router
from .notify import router as notify_router
from .kite import router as kite_router

api = APIRouter()
api.include_router(health_router)
api.include_router(admin_router)
api.include_router(notify_router)
api.include_router(kite_router)
