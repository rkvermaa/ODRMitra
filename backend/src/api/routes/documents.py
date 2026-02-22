"""Document upload and management routes"""

import uuid

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.background import BackgroundTasks
from sqlalchemy import select

from src.api.dependencies import DBSession, CurrentUserId
from src.core.logging import log
from src.core.cloudinary_upload import upload_to_cloudinary
from src.db.models.document import DisputeDocument, AnalysisStatus
from src.db.models.dispute import Dispute

router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    dispute_id: str
    filename: str
    original_filename: str
    doc_type: str
    file_url: str
    file_size: int
    analysis_status: str
    analysis_result: dict | None
    extracted_amount: float | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post(
    "/{dispute_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    dispute_id: str,
    user_id: CurrentUserId,
    db: DBSession,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
):
    """Upload a document for a dispute — stored in Cloudinary."""
    # Verify dispute exists and user has access
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if str(dispute.claimant_id) != user_id and str(dispute.respondent_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Read file content
    content = await file.read()
    original_filename = file.filename or "unknown"
    saved_filename = f"{uuid.uuid4()}_{original_filename}"

    # Upload to Cloudinary
    try:
        upload_result = await upload_to_cloudinary(
            file_content=content,
            filename=saved_filename,
            folder=f"odrmitra/disputes/{dispute_id}",
        )
        file_url = upload_result["url"]
    except Exception as e:
        log.error(f"Cloudinary upload failed, falling back to local: {e}")
        # Fallback: save locally if Cloudinary fails
        from pathlib import Path
        upload_dir = Path("uploads") / dispute_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / saved_filename
        file_path.write_bytes(content)
        file_url = str(file_path)

    doc = DisputeDocument(
        dispute_id=dispute_id,
        filename=saved_filename,
        original_filename=original_filename,
        doc_type=doc_type,
        file_url=file_url,
        file_size=len(content),
        analysis_status=AnalysisStatus.PENDING.value,
        uploaded_by=user_id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Trigger background RAG indexing for the case document
    from src.rag.index_service import index_case_document, fire_and_forget
    fire_and_forget(index_case_document(str(doc.id), dispute_id))

    return DocumentResponse(
        id=str(doc.id),
        dispute_id=str(doc.dispute_id),
        filename=doc.filename,
        original_filename=doc.original_filename,
        doc_type=doc.doc_type,
        file_url=doc.file_url,
        file_size=doc.file_size,
        analysis_status=doc.analysis_status,
        analysis_result=doc.analysis_result,
        extracted_amount=float(doc.extracted_amount) if doc.extracted_amount else None,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{dispute_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    dispute_id: str,
    user_id: CurrentUserId,
    db: DBSession,
):
    """List documents for a dispute."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if str(dispute.claimant_id) != user_id and str(dispute.respondent_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(DisputeDocument)
        .where(DisputeDocument.dispute_id == dispute_id)
        .order_by(DisputeDocument.created_at.desc())
    )
    docs = result.scalars().all()

    return [
        DocumentResponse(
            id=str(d.id),
            dispute_id=str(d.dispute_id),
            filename=d.filename,
            original_filename=d.original_filename,
            doc_type=d.doc_type,
            file_url=d.file_url,
            file_size=d.file_size,
            analysis_status=d.analysis_status,
            analysis_result=d.analysis_result,
            extracted_amount=float(d.extracted_amount) if d.extracted_amount else None,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]
