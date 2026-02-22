"""WhatsApp channel routes"""

from fastapi import APIRouter
from .connection import router as connection_router
from .webhook import router as webhook_router
from .auth import router as auth_router

router = APIRouter(tags=["whatsapp"])

# Connection management (connect, disconnect, status, send)
router.include_router(connection_router)

# Webhook for incoming messages from Baileys service
router.include_router(webhook_router, prefix="/webhook")

# Auth storage API for Baileys service (database-backed credentials)
router.include_router(auth_router, prefix="/auth")
