"""WhatsApp auth storage API — Database-backed Baileys credentials for ODRMitra"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.core.logging import log
from src.db.session import get_db
from src.db.models.whatsapp_auth import WhatsAppAuth

router = APIRouter()


class AuthCredsRequest(BaseModel):
    """Request to update auth credentials."""
    creds: dict


class AuthKeysRequest(BaseModel):
    """Request to replace all auth keys."""
    keys: dict


class AuthKeysPatchRequest(BaseModel):
    """Request to patch (merge) auth keys."""
    set_keys: dict | None = None
    delete_keys: list[str] | None = None


class AuthResponse(BaseModel):
    """Auth credentials response."""
    creds: dict
    keys: dict
    has_credentials: bool


def verify_api_key(x_api_key: str | None) -> bool:
    """Verify the API key from Baileys service."""
    expected = settings.get("baileys_api_key", "baileys-secret-key")
    return x_api_key == expected


async def get_auth_by_session(db: AsyncSession, session_id: str) -> WhatsAppAuth | None:
    """Get WhatsAppAuth by session_id.

    Session ID could be WhatsAppAuth.id (admin bot flow) or
    WhatsAppAuth.user_id (original per-user flow).
    """
    import uuid as _uuid
    try:
        sid = _uuid.UUID(session_id)
    except ValueError:
        return None

    # Try as WhatsAppAuth.id first (admin bot flow)
    result = await db.execute(
        select(WhatsAppAuth).where(WhatsAppAuth.id == sid)
    )
    auth = result.scalar_one_or_none()
    if auth:
        return auth

    # Fallback: try as user_id (original flow)
    result = await db.execute(
        select(WhatsAppAuth).where(WhatsAppAuth.user_id == sid)
    )
    return result.scalar_one_or_none()


@router.get("/restorable")
async def list_restorable_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """List all sessions that have saved credentials and can be auto-restored."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    result = await db.execute(select(WhatsAppAuth))
    all_auth = result.scalars().all()

    restorable = []
    for auth in all_auth:
        if auth.has_credentials:
            restorable.append({
                "session_id": str(auth.id),
                "user_id": str(auth.user_id),
                "phone_number": auth.phone_number,
                "status": auth.status,
            })

    return {"sessions": restorable}


@router.get("/{session_id}", response_model=AuthResponse)
async def get_auth(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Get auth credentials for a WhatsApp session."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    auth = await get_auth_by_session(db, session_id)

    if not auth:
        return AuthResponse(creds={}, keys={}, has_credentials=False)

    return AuthResponse(
        creds=auth.creds or {},
        keys=auth.keys or {},
        has_credentials=auth.has_credentials,
    )


@router.put("/{session_id}/creds")
async def update_creds(
    session_id: str,
    request: AuthCredsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Update auth credentials."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    auth = await get_auth_by_session(db, session_id)

    if not auth:
        # Auto-create — only for legacy per-user flow where session_id = user_id
        auth = WhatsAppAuth(
            user_id=session_id,
            creds=request.creds,
            keys={},
        )
        db.add(auth)
    else:
        auth.creds = request.creds
        auth.updated_at = datetime.now(timezone.utc)

    auth.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    log.info(f"Updated creds for session {session_id}")
    return {"success": True}


@router.put("/{session_id}/keys")
async def update_keys(
    session_id: str,
    request: AuthKeysRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Replace all auth keys."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    auth = await get_auth_by_session(db, session_id)

    if not auth:
        auth = WhatsAppAuth(user_id=session_id, creds={}, keys=request.keys)
        db.add(auth)
    else:
        auth.keys = request.keys
        auth.updated_at = datetime.now(timezone.utc)

    auth.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True}


@router.patch("/{session_id}/keys")
async def patch_keys(
    session_id: str,
    request: AuthKeysPatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Patch auth keys (partial update)."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    auth = await get_auth_by_session(db, session_id)

    if not auth:
        auth = WhatsAppAuth(user_id=session_id, creds={}, keys={})
        db.add(auth)
        await db.flush()

    current_keys = dict(auth.keys or {})

    if request.set_keys:
        current_keys.update(request.set_keys)

    if request.delete_keys:
        for key in request.delete_keys:
            current_keys.pop(key, None)

    auth.keys = current_keys
    auth.updated_at = datetime.now(timezone.utc)
    auth.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True}


@router.delete("/{session_id}")
async def delete_auth(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Delete auth credentials (called on logout)."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    auth = await get_auth_by_session(db, session_id)

    if auth:
        await db.delete(auth)
        await db.commit()
        log.info(f"Deleted auth for session {session_id}")

    return {"success": True}
