"""Dispute CRUD routes"""

import random
from datetime import date

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from src.api.dependencies import DBSession, CurrentUserId
from src.db.models.dispute import Dispute, DisputeStatus
from src.db.models.user import User

router = APIRouter()


class DisputeCreate(BaseModel):
    title: str
    description: str | None = None
    category: str = "delayed_payment"
    respondent_name: str | None = None
    respondent_mobile: str | None = None
    respondent_email: str | None = None
    respondent_category: str | None = None
    respondent_pan: str | None = None
    respondent_gstin: str | None = None
    respondent_state: str | None = None
    respondent_district: str | None = None
    respondent_pin_code: str | None = None
    respondent_address: str | None = None
    claimed_amount: float | None = None
    invoice_amount: float | None = None
    amount_received: float | None = None
    principal_amount: float | None = None
    interest_rate: float | None = None
    interest_start_date: date | None = None
    interest_amount: float | None = None
    total_amount_due: float | None = None
    po_number: str | None = None
    po_date: date | None = None
    payment_terms: str | None = None
    goods_services_description: str | None = None
    cause_of_action: str | None = None
    relief_sought: str | None = None
    correspondence_summary: str | None = None
    buyer_objections: list[dict] | None = None
    msefc_council: str | None = None


class DisputeUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    sub_category: str | None = None
    respondent_name: str | None = None
    respondent_mobile: str | None = None
    respondent_email: str | None = None
    respondent_category: str | None = None
    respondent_pan: str | None = None
    respondent_gstin: str | None = None
    respondent_state: str | None = None
    respondent_district: str | None = None
    respondent_pin_code: str | None = None
    respondent_address: str | None = None
    claimed_amount: float | None = None
    invoice_amount: float | None = None
    amount_received: float | None = None
    principal_amount: float | None = None
    interest_rate: float | None = None
    interest_start_date: date | None = None
    interest_amount: float | None = None
    total_amount_due: float | None = None
    po_number: str | None = None
    po_date: date | None = None
    payment_terms: str | None = None
    goods_services_description: str | None = None
    cause_of_action: str | None = None
    relief_sought: str | None = None
    correspondence_summary: str | None = None
    buyer_objections: list[dict] | None = None
    msefc_council: str | None = None


class DisputeResponse(BaseModel):
    id: str
    case_number: str
    title: str
    description: str | None
    category: str
    sub_category: str | None
    status: str
    # Respondent
    respondent_name: str | None
    respondent_mobile: str | None
    respondent_email: str | None
    respondent_category: str | None
    respondent_pan: str | None
    respondent_gstin: str | None
    respondent_state: str | None
    respondent_district: str | None
    respondent_pin_code: str | None
    respondent_address: str | None
    # Financial
    claimed_amount: float | None
    invoice_amount: float | None
    amount_received: float | None
    principal_amount: float | None
    interest_rate: float | None
    interest_start_date: date | None
    interest_amount: float | None
    total_amount_due: float | None
    # Transaction
    po_number: str | None
    po_date: date | None
    payment_terms: str | None
    goods_services_description: str | None
    # SOC narrative
    cause_of_action: str | None
    relief_sought: str | None
    correspondence_summary: str | None
    buyer_objections: list[dict] | None
    msefc_council: str | None
    # AI
    ai_classification: dict | None
    ai_missing_docs: dict | None
    ai_outcome_prediction: dict | None
    # Meta
    claimant_id: str
    respondent_id: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


def _to_float(val) -> float | None:
    return float(val) if val is not None else None


def _dispute_to_response(d: Dispute) -> DisputeResponse:
    """Convert a Dispute ORM instance to a DisputeResponse."""
    return DisputeResponse(
        id=str(d.id),
        case_number=d.case_number,
        title=d.title,
        description=d.description,
        category=d.category,
        sub_category=d.sub_category,
        status=d.status,
        respondent_name=d.respondent_name,
        respondent_mobile=d.respondent_mobile,
        respondent_email=d.respondent_email,
        respondent_category=d.respondent_category,
        respondent_pan=d.respondent_pan,
        respondent_gstin=d.respondent_gstin,
        respondent_state=d.respondent_state,
        respondent_district=d.respondent_district,
        respondent_pin_code=d.respondent_pin_code,
        respondent_address=d.respondent_address,
        claimed_amount=_to_float(d.claimed_amount),
        invoice_amount=_to_float(d.invoice_amount),
        amount_received=_to_float(d.amount_received),
        principal_amount=_to_float(d.principal_amount),
        interest_rate=_to_float(d.interest_rate),
        interest_start_date=d.interest_start_date,
        interest_amount=_to_float(d.interest_amount),
        total_amount_due=_to_float(d.total_amount_due),
        po_number=d.po_number,
        po_date=d.po_date,
        payment_terms=d.payment_terms,
        goods_services_description=d.goods_services_description,
        cause_of_action=d.cause_of_action,
        relief_sought=d.relief_sought,
        correspondence_summary=d.correspondence_summary,
        buyer_objections=d.buyer_objections,
        msefc_council=d.msefc_council,
        ai_classification=d.ai_classification,
        ai_missing_docs=d.ai_missing_docs,
        ai_outcome_prediction=d.ai_outcome_prediction,
        claimant_id=str(d.claimant_id),
        respondent_id=str(d.respondent_id) if d.respondent_id else None,
        created_at=d.created_at.isoformat(),
        updated_at=d.updated_at.isoformat(),
    )


async def _generate_case_number(db) -> str:
    """Generate unique case number: ODR-2026-XXXX."""
    result = await db.execute(select(func.count(Dispute.id)))
    count = result.scalar() or 0
    return f"ODR-2026-{count + 1:04d}"


@router.get("", response_model=list[DisputeResponse])
async def list_disputes(user_id: CurrentUserId, db: DBSession):
    """List disputes for the current user (as claimant or respondent)."""
    result = await db.execute(
        select(Dispute)
        .where(
            (Dispute.claimant_id == user_id) | (Dispute.respondent_id == user_id)
        )
        .order_by(Dispute.created_at.desc())
    )
    disputes = result.scalars().all()
    return [_dispute_to_response(d) for d in disputes]


@router.post("", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def create_dispute(
    data: DisputeCreate,
    user_id: CurrentUserId,
    db: DBSession,
):
    """Create a new dispute."""
    case_number = await _generate_case_number(db)

    dispute = Dispute(
        case_number=case_number,
        claimant_id=user_id,
        title=data.title,
        description=data.description,
        category=data.category,
        respondent_name=data.respondent_name,
        respondent_mobile=data.respondent_mobile,
        respondent_email=data.respondent_email,
        respondent_category=data.respondent_category,
        respondent_pan=data.respondent_pan,
        respondent_gstin=data.respondent_gstin,
        respondent_state=data.respondent_state,
        respondent_district=data.respondent_district,
        respondent_pin_code=data.respondent_pin_code,
        respondent_address=data.respondent_address,
        claimed_amount=data.claimed_amount,
        invoice_amount=data.invoice_amount,
        amount_received=data.amount_received,
        principal_amount=data.principal_amount,
        interest_rate=data.interest_rate,
        interest_start_date=data.interest_start_date,
        interest_amount=data.interest_amount,
        total_amount_due=data.total_amount_due,
        po_number=data.po_number,
        po_date=data.po_date,
        payment_terms=data.payment_terms,
        goods_services_description=data.goods_services_description,
        cause_of_action=data.cause_of_action,
        relief_sought=data.relief_sought,
        correspondence_summary=data.correspondence_summary,
        buyer_objections=data.buyer_objections,
        msefc_council=data.msefc_council,
        status=DisputeStatus.FILED.value,
    )
    db.add(dispute)
    await db.flush()
    await db.refresh(dispute)

    return _dispute_to_response(dispute)


@router.get("/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(dispute_id: str, user_id: CurrentUserId, db: DBSession):
    """Get a single dispute by ID."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Check access
    if str(dispute.claimant_id) != user_id and str(dispute.respondent_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _dispute_to_response(dispute)


@router.patch("/{dispute_id}", response_model=DisputeResponse)
async def update_dispute(
    dispute_id: str,
    data: DisputeUpdate,
    user_id: CurrentUserId,
    db: DBSession,
):
    """Update dispute fields."""
    result = await db.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if str(dispute.claimant_id) != user_id:
        raise HTTPException(status_code=403, detail="Only claimant can update")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dispute, field, value)

    await db.flush()
    await db.refresh(dispute)

    return _dispute_to_response(dispute)
