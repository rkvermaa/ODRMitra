"""WhatsApp connection management — Baileys Service integration for ODRMitra"""

import asyncio
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import CurrentUserId, DBSession
from src.config import settings
from src.core.logging import log
from src.db.models.user import User
from src.db.models.whatsapp_auth import WhatsAppAuth
from sqlalchemy import select

router = APIRouter()


class WhatsAppStatusResponse(BaseModel):
    """WhatsApp connection status response."""
    status: str  # not_started, connecting, qr, connected, disconnected
    connected: bool
    phone_number: str | None = None
    qr_code: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a WhatsApp message."""
    to: str
    message: str


def get_baileys_url() -> str:
    """Get Baileys service base URL."""
    return settings.get("baileys_service_url", "http://127.0.0.1:3001")


def get_baileys_headers() -> dict:
    """Get headers for Baileys service requests."""
    return {
        "X-API-Key": settings.get("baileys_api_key", "baileys-secret-key"),
        "Content-Type": "application/json",
    }


@router.post("/connect", response_model=WhatsAppStatusResponse)
async def connect_whatsapp(
    user_id: CurrentUserId,
    db: DBSession,
):
    """Start WhatsApp connection. Returns QR code for scanning."""
    baileys_url = get_baileys_url()
    headers = get_baileys_headers()

    # Ensure WhatsAppAuth record exists
    result = await db.execute(
        select(WhatsAppAuth).where(WhatsAppAuth.user_id == user_id)
    )
    auth = result.scalar_one_or_none()

    if not auth:
        auth = WhatsAppAuth(user_id=user_id, status="connecting")
        db.add(auth)
        await db.flush()
    else:
        auth.status = "connecting"

    await db.commit()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_response = await client.post(
                f"{baileys_url}/sessions/{user_id}/start",
                headers=headers,
            )

            if start_response.status_code != 200:
                log.warning(f"Start session response: {start_response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to start WhatsApp session",
                )

            data = start_response.json()

            if data.get("status") == "connected":
                phone_number = data.get("phoneNumber")
                auth.status = "connected"
                auth.phone_number = phone_number

                # Update user flag
                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.whatsapp_connected = True
                await db.commit()

                return WhatsAppStatusResponse(
                    status="connected",
                    connected=True,
                    phone_number=phone_number,
                )

            if data.get("status") == "qr" and data.get("qr"):
                return WhatsAppStatusResponse(
                    status="qr",
                    connected=False,
                    qr_code=data.get("qr"),
                )

            # Still connecting, poll
            await asyncio.sleep(2)
            return await get_whatsapp_status(user_id, db)

    except httpx.HTTPError as e:
        log.error(f"Failed to connect WhatsApp for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp service unavailable. Make sure Baileys service is running.",
        )


@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    user_id: CurrentUserId,
    db: DBSession,
):
    """Get WhatsApp connection status."""
    baileys_url = get_baileys_url()
    headers = get_baileys_headers()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{baileys_url}/sessions/{user_id}/status",
                headers=headers,
            )

            if response.status_code != 200:
                return WhatsAppStatusResponse(status="not_started", connected=False)

            data = response.json()
            session_status = data.get("status", "not_started")
            is_connected = data.get("connected", False)
            phone_number = data.get("phoneNumber")
            qr_code = data.get("qr")

            # Update DB if connected
            if is_connected:
                result = await db.execute(
                    select(WhatsAppAuth).where(WhatsAppAuth.user_id == user_id)
                )
                auth = result.scalar_one_or_none()
                if auth:
                    auth.status = "connected"
                    auth.phone_number = phone_number

                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.whatsapp_connected = True
                await db.commit()

            return WhatsAppStatusResponse(
                status=session_status,
                connected=is_connected,
                phone_number=phone_number,
                qr_code=qr_code,
            )

    except httpx.HTTPError as e:
        log.error(f"Failed to get WhatsApp status for user {user_id}: {e}")
        return WhatsAppStatusResponse(status="service_unavailable", connected=False)


@router.post("/disconnect")
async def disconnect_whatsapp(
    user_id: CurrentUserId,
    db: DBSession,
):
    """Soft disconnect (keeps credentials)."""
    baileys_url = get_baileys_url()
    headers = get_baileys_headers()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{baileys_url}/sessions/{user_id}/disconnect",
                headers=headers,
            )

        result = await db.execute(
            select(WhatsAppAuth).where(WhatsAppAuth.user_id == user_id)
        )
        auth = result.scalar_one_or_none()
        if auth:
            auth.status = "disconnected"

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.whatsapp_connected = False
        await db.commit()

        return {"success": True, "message": "Disconnected. Reconnect without QR scan."}

    except httpx.HTTPError as e:
        log.error(f"Failed to disconnect WhatsApp for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp service unavailable",
        )


@router.post("/send")
async def send_whatsapp_message(
    user_id: CurrentUserId,
    request: SendMessageRequest,
    db: DBSession,
):
    """Send a WhatsApp message."""
    baileys_url = get_baileys_url()
    headers = get_baileys_headers()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{baileys_url}/sessions/{user_id}/send",
                json={"to": request.to, "message": request.message},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        log.error(f"Failed to send WhatsApp message for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send message",
        )


@router.post("/reset")
async def reset_whatsapp(
    user_id: CurrentUserId,
    db: DBSession,
):
    """Reset WhatsApp session (clear credentials and start fresh)."""
    baileys_url = get_baileys_url()
    headers = get_baileys_headers()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{baileys_url}/sessions/{user_id}/reset",
                headers=headers,
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to reset WhatsApp session",
                )
            return response.json()

    except httpx.HTTPError as e:
        log.error(f"Failed to reset WhatsApp for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp service unavailable",
        )
