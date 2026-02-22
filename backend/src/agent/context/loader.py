"""Context loader — fetches user/dispute info from DB for agent prompts."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import log


async def load_seller_profile(user_id: str, db: AsyncSession) -> dict[str, Any]:
    """Fetch seller (claimant) profile from database.

    Returns dict with seller info for injection into voice prompt.
    """
    from src.db.models.user import User

    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            log.warning(f"User {user_id} not found for seller profile")
            return {}

        return {
            "name": user.name or "",
            "mobile_number": user.mobile_number or "",
            "organization_name": user.organization_name or "",
            "udyam_registration": user.udyam_registration or "",
            "gstin": user.gstin or "",
            "state": user.state or "",
            "district": user.district or "",
            "business_type": user.business_type or "",
            "email": user.email or "",
        }

    except Exception as e:
        log.error(f"Failed to load seller profile: {e}")
        return {}


def build_seller_context(profile: dict[str, Any]) -> str:
    """Build a text block describing the seller for prompt injection."""
    if not profile or not profile.get("name"):
        return ""

    parts = ["## SELLER (LOGGED-IN USER) INFO — from database"]
    parts.append(f"Name: {profile['name']}")

    if profile.get("mobile_number"):
        parts.append(f"Registered Mobile: {profile['mobile_number']}")
    if profile.get("organization_name"):
        parts.append(f"Organization: {profile['organization_name']}")
    if profile.get("udyam_registration"):
        parts.append(f"Udyam Number: {profile['udyam_registration']}")
    if profile.get("business_type"):
        parts.append(f"Business Type: {profile['business_type']}")
    if profile.get("gstin"):
        parts.append(f"GSTIN: {profile['gstin']}")
    if profile.get("state"):
        state_str = profile["state"]
        if profile.get("district"):
            state_str += f", {profile['district']}"
        parts.append(f"Location: {state_str}")

    parts.append("")
    parts.append(
        "Use this info to personalize the conversation. "
        "The seller_mobile field for case filing should be this registered mobile number "
        "(but still ask for confirmation)."
    )

    return "\n".join(parts)


async def load_dispute_context(dispute_id: str, user_id: str, db: AsyncSession) -> dict[str, Any]:
    """Fetch dispute details from DB for existing-case voice mode.

    Only returns dispute if it belongs to the given user (claimant).
    """
    from src.db.models.dispute import Dispute

    try:
        result = await db.execute(
            select(Dispute)
            .where(Dispute.id == dispute_id, Dispute.claimant_id == user_id)
            .options(selectinload(Dispute.documents))
        )
        dispute = result.scalar_one_or_none()
        if not dispute:
            log.warning(f"Dispute {dispute_id} not found for user {user_id}")
            return {}

        docs = []
        for doc in (dispute.documents or []):
            docs.append({
                "name": doc.original_filename or "Unknown",
                "type": doc.doc_type or "other",
                "status": doc.analysis_status or "pending",
            })

        return {
            "case_number": dispute.case_number,
            "title": dispute.title or "",
            "status": dispute.status or "",
            "category": dispute.category or "",
            "respondent_name": dispute.respondent_name or "",
            "respondent_mobile": dispute.respondent_mobile or "",
            "invoice_amount": str(dispute.invoice_amount) if dispute.invoice_amount else "",
            "claimed_amount": str(dispute.claimed_amount) if dispute.claimed_amount else "",
            "goods_services_description": dispute.goods_services_description or "",
            "created_at": dispute.created_at.strftime("%d %b %Y") if dispute.created_at else "",
            "documents": docs,
            "ai_classification": dispute.ai_classification,
            "ai_outcome_prediction": dispute.ai_outcome_prediction,
            "ai_missing_docs": dispute.ai_missing_docs,
        }

    except Exception as e:
        log.error(f"Failed to load dispute context: {e}")
        return {}


def build_dispute_context(dispute_info: dict[str, Any]) -> str:
    """Format dispute details as text block for prompt injection."""
    if not dispute_info or not dispute_info.get("case_number"):
        return ""

    parts = ["## CASE DETAILS — from database"]
    parts.append(f"Case Number: {dispute_info['case_number']}")
    parts.append(f"Title: {dispute_info['title']}")
    parts.append(f"Status: {dispute_info['status']}")
    parts.append(f"Category: {dispute_info['category']}")
    parts.append(f"Filed on: {dispute_info['created_at']}")

    if dispute_info.get("respondent_name"):
        parts.append(f"Buyer (Respondent): {dispute_info['respondent_name']}")
    if dispute_info.get("respondent_mobile"):
        parts.append(f"Buyer Mobile: {dispute_info['respondent_mobile']}")
    if dispute_info.get("goods_services_description"):
        parts.append(f"Goods/Services: {dispute_info['goods_services_description']}")
    if dispute_info.get("invoice_amount"):
        parts.append(f"Invoice Amount: ₹{dispute_info['invoice_amount']}")
    if dispute_info.get("claimed_amount"):
        parts.append(f"Claimed Amount: ₹{dispute_info['claimed_amount']}")

    # Documents
    docs = dispute_info.get("documents", [])
    if docs:
        parts.append(f"\nDocuments ({len(docs)}):")
        for d in docs:
            parts.append(f"  - {d['name']} ({d['type']}) — {d['status']}")

    # AI analysis
    if dispute_info.get("ai_classification"):
        cls = dispute_info["ai_classification"]
        parts.append(f"\nAI Classification: {cls.get('sub_category', 'N/A')} (confidence: {cls.get('confidence', 'N/A')})")

    if dispute_info.get("ai_outcome_prediction"):
        pred = dispute_info["ai_outcome_prediction"]
        parts.append(f"AI Outcome Prediction: {pred.get('predicted_outcome', 'N/A')}")

    if dispute_info.get("ai_missing_docs"):
        missing = dispute_info["ai_missing_docs"]
        if missing.get("missing"):
            parts.append(f"Missing Documents: {', '.join(missing['missing'])}")

    return "\n".join(parts)
