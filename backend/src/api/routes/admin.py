"""Admin routes — bot management, all cases, bot numbers, knowledge base"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import DBSession, get_current_user_id
from src.core.security import get_require_admin
from src.core.logging import log
from src.core.cloudinary_upload import upload_to_cloudinary
from src.db.session import get_db
from src.db.models.whatsapp_auth import WhatsAppAuth
from src.db.models.dispute import Dispute
from src.db.models.user import User
from src.db.models.knowledge_document import KnowledgeDocument, IndexStatus

router = APIRouter()

# Admin dependency
RequireAdmin = Annotated[str, Depends(get_require_admin())]


# ─── Schemas ─────────────────────────────────────────

class BotResponse(BaseModel):
    id: str
    label: str | None
    phone_number: str | None
    status: str
    created_at: str | None

    model_config = {"from_attributes": True}


class ConnectBotResponse(BaseModel):
    bot_id: str
    connected: bool
    phone_number: str | None
    qr_code: str | None


class BotStatusResponse(BaseModel):
    connected: bool
    phone_number: str | None
    status: str
    qr_code: str | None = None


class BotNumberResponse(BaseModel):
    phone_number: str
    label: str | None


class DisputeResponse(BaseModel):
    id: str
    case_number: str
    title: str
    category: str
    status: str
    claimed_amount: float | None
    invoice_amount: float | None
    respondent_name: str | None
    claimant_id: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ─── Bot Management (admin-only) ─────────────────────

@router.get("/bots", response_model=list[BotResponse])
async def list_bots(admin_id: RequireAdmin, db: DBSession):
    """List all WhatsApp bots for this admin."""
    result = await db.execute(
        select(WhatsAppAuth).where(
            WhatsAppAuth.user_id == uuid.UUID(admin_id)
        ).order_by(WhatsAppAuth.created_at)
    )
    bots = result.scalars().all()
    return [
        BotResponse(
            id=str(b.id),
            label=b.label,
            phone_number=b.phone_number,
            status=b.status,
            created_at=b.created_at.isoformat() if b.created_at else None,
        )
        for b in bots
    ]


@router.post("/bots", response_model=ConnectBotResponse)
async def connect_bot(admin_id: RequireAdmin, db: DBSession):
    """Start connecting a new WhatsApp bot. Proxies to Baileys service."""
    import httpx
    from src.api.routes.channel.whatsapp.connection import get_baileys_url, get_baileys_headers

    # Create a new WhatsAppAuth record
    bot = WhatsAppAuth(
        user_id=uuid.UUID(admin_id),
        label=f"Bot {await _count_bots(db, admin_id) + 1}",
        status="connecting",
    )
    db.add(bot)
    await db.commit()  # Commit NOW so Baileys can find this record when storing creds
    await db.refresh(bot)

    bot_id = str(bot.id)

    # Try to connect via Baileys service
    try:
        baileys_url = get_baileys_url()
        headers = get_baileys_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{baileys_url}/sessions/{bot_id}/start",
                headers=headers,
            )
            data = resp.json()

            if data.get("status") == "connected":
                bot.status = "connected"
                bot.phone_number = data.get("phoneNumber")
                return ConnectBotResponse(
                    bot_id=bot_id,
                    connected=True,
                    phone_number=bot.phone_number,
                    qr_code=None,
                )

            return ConnectBotResponse(
                bot_id=bot_id,
                connected=False,
                phone_number=None,
                qr_code=data.get("qr"),
            )
    except Exception:
        # Baileys service not reachable — return bot_id for polling
        return ConnectBotResponse(
            bot_id=bot_id,
            connected=False,
            phone_number=None,
            qr_code=None,
        )


@router.get("/bots/{bot_id}/status", response_model=BotStatusResponse)
async def get_bot_status(bot_id: str, admin_id: RequireAdmin, db: DBSession):
    """Get specific bot connection status."""
    bot = await _get_bot(db, bot_id, admin_id)

    # Also check Baileys service for live status
    try:
        import httpx
        from src.api.routes.channel.whatsapp.connection import get_baileys_url, get_baileys_headers

        baileys_url = get_baileys_url()
        headers = get_baileys_headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{baileys_url}/sessions/{bot_id}/status",
                headers=headers,
            )
            data = resp.json()

            if data.get("connected"):
                if not bot.phone_number or bot.status != "connected":
                    bot.phone_number = data.get("phoneNumber")
                    bot.status = "connected"
                    await db.commit()

            return BotStatusResponse(
                connected=data.get("connected", False),
                phone_number=bot.phone_number,
                status=data.get("status", bot.status),
                qr_code=data.get("qr"),
            )
    except Exception:
        return BotStatusResponse(
            connected=bot.status == "connected",
            phone_number=bot.phone_number,
            status=bot.status,
        )


@router.post("/bots/{bot_id}/disconnect")
async def disconnect_bot(bot_id: str, admin_id: RequireAdmin, db: DBSession):
    """Disconnect a WhatsApp bot."""
    bot = await _get_bot(db, bot_id, admin_id)

    try:
        import httpx
        from src.api.routes.channel.whatsapp.connection import get_baileys_url, get_baileys_headers

        baileys_url = get_baileys_url()
        headers = get_baileys_headers()
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{baileys_url}/sessions/{bot_id}/disconnect",
                headers=headers,
            )
    except Exception:
        pass

    bot.status = "disconnected"
    return {"success": True}


@router.post("/bots/{bot_id}/reset")
async def reset_bot(bot_id: str, admin_id: RequireAdmin, db: DBSession):
    """Reset a WhatsApp bot session."""
    bot = await _get_bot(db, bot_id, admin_id)

    try:
        import httpx
        from src.api.routes.channel.whatsapp.connection import get_baileys_url, get_baileys_headers

        baileys_url = get_baileys_url()
        headers = get_baileys_headers()
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{baileys_url}/sessions/{bot_id}/reset",
                headers=headers,
            )
    except Exception:
        pass

    bot.status = "disconnected"
    bot.creds = {}
    bot.keys = {}
    bot.phone_number = None
    return {"success": True}


# ─── All Cases (admin-only) ──────────────────────────

@router.get("/cases", response_model=list[DisputeResponse])
async def list_all_cases(admin_id: RequireAdmin, db: DBSession):
    """List ALL disputes across the platform (admin view)."""
    result = await db.execute(
        select(Dispute).order_by(Dispute.created_at.desc())
    )
    disputes = result.scalars().all()
    return [
        DisputeResponse(
            id=str(d.id),
            case_number=d.case_number,
            title=d.title,
            category=d.category,
            status=d.status,
            claimed_amount=float(d.claimed_amount) if d.claimed_amount else None,
            invoice_amount=float(d.invoice_amount) if d.invoice_amount else None,
            respondent_name=d.respondent_name,
            claimant_id=str(d.claimant_id),
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )
        for d in disputes
    ]


# ─── Bot Numbers (public-ish, for seller portal) ─────

@router.get("/bot-numbers", response_model=list[BotNumberResponse])
async def get_bot_numbers(db: DBSession):
    """Return active bot phone numbers. No admin auth required — sellers need to see these."""
    result = await db.execute(
        select(WhatsAppAuth).where(
            WhatsAppAuth.status == "connected",
            WhatsAppAuth.phone_number.isnot(None),
        )
    )
    bots = result.scalars().all()
    return [
        BotNumberResponse(phone_number=b.phone_number, label=b.label)
        for b in bots
    ]


# ─── Knowledge Base Schemas ───────────────────────────

class KnowledgeDocResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_url: str
    file_size: int
    doc_category: str
    description: str | None
    index_status: str
    index_error: str | None
    chunk_count: int
    uploaded_by: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    indexed_documents: int
    failed_documents: int
    pending_documents: int
    total_chunks: int
    legal_collection: dict
    case_docs_collection: dict


# ─── Knowledge Base (admin-only) ─────────────────────

@router.get("/knowledge-base", response_model=list[KnowledgeDocResponse])
async def list_knowledge_docs(admin_id: RequireAdmin, db: DBSession):
    """List all admin-uploaded knowledge documents."""
    result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        KnowledgeDocResponse(
            id=str(d.id),
            filename=d.filename,
            original_filename=d.original_filename,
            file_url=d.file_url,
            file_size=d.file_size,
            doc_category=d.doc_category,
            description=d.description,
            index_status=d.index_status,
            index_error=d.index_error,
            chunk_count=d.chunk_count,
            uploaded_by=str(d.uploaded_by),
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )
        for d in docs
    ]


@router.post("/knowledge-base/upload", response_model=KnowledgeDocResponse, status_code=201)
async def upload_knowledge_doc(
    admin_id: RequireAdmin,
    db: DBSession,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_category: str = Form("other"),
    description: str = Form(""),
):
    """Upload a legal document for the knowledge base."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    original_filename = file.filename
    # Sanitize filename for Cloudinary — remove special chars that break public_id
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', original_filename)
    saved_filename = f"{uuid.uuid4()}_{safe_name}"

    # Upload to Cloudinary
    try:
        upload_result = await upload_to_cloudinary(
            file_content=content,
            filename=saved_filename,
            folder="odrmitra/legal-docs",
        )
        file_url = upload_result["url"]
    except Exception as e:
        log.error(f"Cloudinary upload failed for knowledge doc: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")

    # Save to DB
    doc = KnowledgeDocument(
        filename=saved_filename,
        original_filename=original_filename,
        file_url=file_url,
        file_size=len(content),
        doc_category=doc_category,
        description=description or None,
        index_status=IndexStatus.PENDING.value,
        uploaded_by=uuid.UUID(admin_id),
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Trigger background indexing (fire-and-forget async task)
    from src.rag.index_service import index_knowledge_document, fire_and_forget
    fire_and_forget(index_knowledge_document(str(doc.id)))

    return KnowledgeDocResponse(
        id=str(doc.id),
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_url=doc.file_url,
        file_size=doc.file_size,
        doc_category=doc.doc_category,
        description=doc.description,
        index_status=doc.index_status,
        index_error=doc.index_error,
        chunk_count=doc.chunk_count,
        uploaded_by=str(doc.uploaded_by),
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.delete("/knowledge-base/{doc_id}")
async def delete_knowledge_doc(
    doc_id: str,
    admin_id: RequireAdmin,
    db: DBSession,
    background_tasks: BackgroundTasks,
):
    """Delete a knowledge document and its Qdrant chunks."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    source = doc.original_filename

    # Delete from Cloudinary (best effort)
    try:
        import cloudinary.uploader
        from src.core.cloudinary_upload import _configure
        _configure()
        # Extract public_id from URL
        if doc.file_url and "cloudinary" in doc.file_url:
            # public_id is the path without extension
            parts = doc.file_url.split("/upload/")
            if len(parts) > 1:
                public_id = parts[1].rsplit(".", 1)[0]
                # Remove version prefix (e.g. v1234567/)
                if public_id.startswith("v") and "/" in public_id:
                    public_id = public_id.split("/", 1)[1]
                cloudinary.uploader.destroy(public_id)
    except Exception as e:
        log.warning(f"Failed to delete from Cloudinary: {e}")

    # Delete from DB
    await db.delete(doc)

    # Delete chunks from Qdrant in background
    from src.rag.index_service import delete_knowledge_document_chunks
    background_tasks.add_task(delete_knowledge_document_chunks, doc_id, source)

    return {"success": True, "deleted": doc_id}


@router.post("/knowledge-base/{doc_id}/reindex")
async def reindex_knowledge_doc(
    doc_id: str,
    admin_id: RequireAdmin,
    db: DBSession,
    background_tasks: BackgroundTasks,
):
    """Re-index a knowledge document."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.index_status = IndexStatus.PENDING.value
    doc.index_error = None

    from src.rag.index_service import index_knowledge_document, fire_and_forget
    fire_and_forget(index_knowledge_document(str(doc.id)))

    return {"success": True, "doc_id": doc_id, "status": "pending"}


@router.get("/knowledge-base/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(admin_id: RequireAdmin, db: DBSession):
    """Get knowledge base statistics."""
    # DB stats
    total = (await db.execute(select(func.count()).select_from(KnowledgeDocument))).scalar() or 0
    indexed = (await db.execute(
        select(func.count()).select_from(KnowledgeDocument).where(
            KnowledgeDocument.index_status == IndexStatus.INDEXED.value
        )
    )).scalar() or 0
    failed = (await db.execute(
        select(func.count()).select_from(KnowledgeDocument).where(
            KnowledgeDocument.index_status == IndexStatus.FAILED.value
        )
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(KnowledgeDocument).where(
            KnowledgeDocument.index_status.in_([
                IndexStatus.PENDING.value, IndexStatus.INDEXING.value
            ])
        )
    )).scalar() or 0
    total_chunks = (await db.execute(
        select(func.sum(KnowledgeDocument.chunk_count))
    )).scalar() or 0

    # Qdrant collection stats
    from src.rag.qdrant_search import QdrantSearch, LEGAL_COLLECTION, CASE_DOCS_COLLECTION
    try:
        legal_info = QdrantSearch.get_collection_info(LEGAL_COLLECTION)
    except Exception:
        legal_info = {"name": LEGAL_COLLECTION, "vectors_count": 0, "points_count": 0}
    try:
        case_info = QdrantSearch.get_collection_info(CASE_DOCS_COLLECTION)
    except Exception:
        case_info = {"name": CASE_DOCS_COLLECTION, "vectors_count": 0, "points_count": 0}

    return KnowledgeStatsResponse(
        total_documents=total,
        indexed_documents=indexed,
        failed_documents=failed,
        pending_documents=pending,
        total_chunks=total_chunks,
        legal_collection=legal_info,
        case_docs_collection=case_info,
    )


# ─── Helpers ──────────────────────────────────────────

async def _get_bot(db: AsyncSession, bot_id: str, admin_id: str) -> WhatsAppAuth:
    """Get a bot by ID, ensuring it belongs to this admin."""
    result = await db.execute(
        select(WhatsAppAuth).where(
            WhatsAppAuth.id == uuid.UUID(bot_id),
            WhatsAppAuth.user_id == uuid.UUID(admin_id),
        )
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )
    return bot


async def _count_bots(db: AsyncSession, admin_id: str) -> int:
    """Count bots for an admin."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count()).where(
            WhatsAppAuth.user_id == uuid.UUID(admin_id)
        )
    )
    return result.scalar() or 0
