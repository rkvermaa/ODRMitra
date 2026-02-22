"""Channel routes — WhatsApp"""

from fastapi import APIRouter
from .whatsapp import router as whatsapp_router

router = APIRouter(prefix="/channel", tags=["channels"])

router.include_router(whatsapp_router, prefix="/whatsapp")
