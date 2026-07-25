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


async def load_user_disputes(user_id: str, db: AsyncSession) -> list[dict[str, Any]]:
    """All disputes filed by this user (newest first) for the case-list block."""
    from src.db.models.dispute import Dispute

    try:
        result = await db.execute(
            select(Dispute)
            .where(Dispute.claimant_id == user_id)
            .options(selectinload(Dispute.documents))
            .order_by(Dispute.created_at.desc())
        )
        disputes = result.scalars().all()

        # Lazy ex-parte check: a silent buyer must never stall a case. This
        # loader owns its session, so commit the transition here.
        import asyncio

        from src.tasks.dispatcher import advance_expired_sod, dispatch_ex_parte_notice

        advanced = [d for d in disputes if advance_expired_sod(d)]
        if advanced:
            await db.commit()
            for d in advanced:
                asyncio.create_task(dispatch_ex_parte_notice(str(d.id)))
    except Exception as e:
        log.error(f"Failed to load user disputes: {e}")
        return []

    out: list[dict[str, Any]] = []
    for d in disputes:
        # What the filing still needs before the case can move forward —
        # mirrors the whatsapp-filing skill's completion requirements.
        missing: list[str] = []
        if not (d.respondent_email or d.respondent_gstin):
            missing.append("buyer email ya GSTIN")
        if not d.respondent_state:
            missing.append("buyer ka state")
        if not d.po_number:
            missing.append("PO number")
        if not d.documents:
            missing.append("invoice document")

        out.append({
            "id": str(d.id),
            "case_number": d.case_number,
            "title": d.title or "",
            "status": d.status or "",
            "claimed_amount": str(d.claimed_amount) if d.claimed_amount else "",
            "respondent_name": d.respondent_name or "",
            "respondent_mobile": d.respondent_mobile or "",
            "intimation_sent_at": (
                d.intimation_sent_at.strftime("%d %b %Y") if d.intimation_sent_at else ""
            ),
            "missing": missing,
        })
    return out


async def load_disputes_against_user(user_id: str, db: AsyncSession) -> list[dict[str, Any]]:
    """Disputes where this user is the RESPONDENT (filed against their mobile)."""
    from src.db.models.dispute import Dispute
    from src.db.models.user import User

    try:
        user = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if not user or not user.mobile_number:
            return []

        digits = user.mobile_number.lstrip("+")
        variants = {digits}
        if digits.startswith("91") and len(digits) == 12:
            variants.add(digits[2:])
        elif len(digits) == 10:
            variants.add(f"91{digits}")

        result = await db.execute(
            select(Dispute)
            .where(
                (Dispute.respondent_mobile.in_(variants))
                | (Dispute.respondent_id == user.id)
            )
            .order_by(Dispute.created_at.desc())
        )
        disputes = result.scalars().all()
    except Exception as e:
        log.error(f"Failed to load disputes against user: {e}")
        return []

    return [
        {
            "id": str(d.id),
            "case_number": d.case_number,
            "title": d.title or "",
            "status": d.status or "",
            "claimed_amount": str(d.claimed_amount) if d.claimed_amount else "",
            "claimant_id": str(d.claimant_id),
        }
        for d in disputes
    ]


def build_respondent_context(disputes: list[dict[str, Any]]) -> str:
    """Block listing complaints FILED AGAINST this user (they are the buyer)."""
    if not disputes:
        return ""

    parts = [
        f"## COMPLAINTS FILED AGAINST THIS USER ({len(disputes)} total)",
        "This user is the RESPONDENT (buyer) in these cases. If they ask",
        '"kya mere khilaf koi complaint hai?" the answer is YES — share the',
        "case details, explain their Section 18 options (respond within 15",
        "days, submit their side / Statement of Defense, or propose a",
        "settlement), and offer to record their response.",
        "",
        "The MOMENT they state their side (admit / partly admit / deny, and",
        "why — e.g. defective goods, already paid), call `submit_defense` with",
        "that case's dispute_id, the response_type, their statement, and any",
        "admitted amount. Do not wait or re-confirm; record it, then explain",
        "the next steps from the tool result.",
        "",
        "Settlement: if BOTH sides' agreement on an amount is on record, call",
        "`finalize_settlement` — it drafts the agreement and WhatsApps the",
        "summary to both parties. Never finalize on one side's offer alone.",
    ]
    for i, d in enumerate(disputes, 1):
        stage = STATUS_LABELS.get(d["status"], d["status"])
        line = f"{i}. {d['case_number']} — {d['title']}"
        if d["claimed_amount"]:
            line += f" | Claimed: ₹{d['claimed_amount']}"
        line += f" | Stage: {stage} | dispute_id: {d['id']}"
        parts.append(line)
    return "\n".join(parts)


def build_case_list_context(disputes: list[dict[str, Any]]) -> str:
    """Numbered list of the user's complaints for prompt injection."""
    if not disputes:
        return "## USER'S COMPLAINTS\nThis user has not filed any complaint yet."

    parts = [f"## USER'S COMPLAINTS ({len(disputes)} total)"]
    for i, d in enumerate(disputes, 1):
        stage = STATUS_LABELS.get(d["status"], d["status"])
        line = f"{i}. {d['case_number']} — {d['title']}"
        if d["respondent_name"]:
            line += f" | Buyer: {d['respondent_name']}"
        if d["claimed_amount"]:
            line += f" | Claimed: ₹{d['claimed_amount']}"
        line += f" | Stage: {stage} | dispute_id: {d['id']}"
        parts.append(line)
        if d["missing"]:
            parts.append(f"   Pending info needed to proceed: {', '.join(d['missing'])}")
        else:
            parts.append("   All key filing info received.")
        if d.get("intimation_sent_at"):
            parts.append(f"   Intimation: SENT on {d['intimation_sent_at']}.")
        elif d.get("respondent_mobile"):
            parts.append(
                "   Intimation: NOT sent yet — buyer mobile is on file, call "
                "send_intimation now."
            )
        else:
            parts.append(
                "   Intimation: NOT sent — buyer mobile number needed first."
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


# Human-readable stage names for the 16-step ODR workflow — the raw codes
# invite the LLM to invent expansions ("dgp" != "Document Gathering Phase").
STATUS_LABELS: dict[str, str] = {
    "filed": "Statement of Claim filed (Step 2)",
    "intimation_sent": "Buyer intimation sent (Step 3)",
    "sod_filed": "Statement of Defence filed (Step 4)",
    "pre_msefc": "Pre-MSEFC mutual settlement stage (Step 5)",
    "dgp": "Digital Guided Pathway — AI outcome prediction (Step 6)",
    "negotiation": "Unmanned Negotiation (Step 7)",
    "msefc": "Referred to MSEFC (Step 8)",
    "scrutiny_soc": "MSEFC scrutiny of claim (Step 9)",
    "notice": "MSEFC notice issued (Step 10)",
    "scrutiny_sod": "MSEFC scrutiny of defence (Step 11)",
    "conciliation_assigned": "Conciliator assigned (Step 12)",
    "conciliation_proceedings": "Conciliation proceedings (Step 13)",
    "conciliation": "Conciliation (Step 13)",
    "arbitration": "Arbitration (Step 14)",
    "resolution": "Resolution / award (Step 15)",
    "closed": "Case closed (Step 16)",
}


def build_dispute_context(dispute_info: dict[str, Any]) -> str:
    """Format dispute details as text block for prompt injection."""
    if not dispute_info or not dispute_info.get("case_number"):
        return ""

    status = dispute_info["status"]
    status_label = STATUS_LABELS.get(status, status)

    parts = ["## CASE DETAILS — from database"]
    parts.append(f"Case Number: {dispute_info['case_number']}")
    parts.append(f"Title: {dispute_info['title']}")
    parts.append(f"Status: {status_label}")
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
