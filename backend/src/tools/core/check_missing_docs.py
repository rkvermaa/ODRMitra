"""Check missing documents tool."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


# Required docs per dispute category
REQUIRED_DOCS = {
    "default": [
        {"type": "invoice", "label": "Invoice / Bill", "mandatory": True},
        {"type": "udyam_certificate", "label": "Udyam Registration Certificate", "mandatory": True},
        {"type": "affidavit", "label": "Affidavit", "mandatory": True},
    ],
    "delayed_payment": [
        {"type": "invoice", "label": "Invoice / Bill", "mandatory": True},
        {"type": "udyam_certificate", "label": "Udyam Registration Certificate", "mandatory": True},
        {"type": "affidavit", "label": "Affidavit", "mandatory": True},
        {"type": "purchase_order", "label": "Purchase Order", "mandatory": False},
        {"type": "delivery_challan", "label": "Delivery Challan / Proof of Delivery", "mandatory": False},
        {"type": "correspondence", "label": "Payment Reminder / Correspondence", "mandatory": False},
    ],
    "non_payment": [
        {"type": "invoice", "label": "Invoice / Bill", "mandatory": True},
        {"type": "udyam_certificate", "label": "Udyam Registration Certificate", "mandatory": True},
        {"type": "affidavit", "label": "Affidavit", "mandatory": True},
        {"type": "purchase_order", "label": "Purchase Order", "mandatory": True},
        {"type": "delivery_challan", "label": "Delivery Challan / Proof of Delivery", "mandatory": True},
        {"type": "correspondence", "label": "Demand Notice / Correspondence", "mandatory": False},
    ],
    "disputed_quality": [
        {"type": "invoice", "label": "Invoice / Bill", "mandatory": True},
        {"type": "udyam_certificate", "label": "Udyam Registration Certificate", "mandatory": True},
        {"type": "affidavit", "label": "Affidavit", "mandatory": True},
        {"type": "contract", "label": "Contract / Agreement with Quality Specs", "mandatory": True},
        {"type": "correspondence", "label": "Quality Objection Correspondence", "mandatory": True},
    ],
}


class CheckMissingDocsTool(BaseTool):
    """Check which documents are missing for a dispute case."""

    name = "check_missing_docs"
    description = (
        "Check which required documents are missing for a dispute case filing. "
        "Compares uploaded documents against mandatory and recommended documents per category."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute to check documents for",
            },
        },
        "required": ["dispute_id"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        dispute_id = arguments["dispute_id"]

        try:
            from src.db.session import async_session_factory
            from src.db.models.dispute import Dispute
            from src.db.models.document import DisputeDocument
            from sqlalchemy import select

            async with async_session_factory() as db:
                # Get dispute
                result = await db.execute(
                    select(Dispute).where(Dispute.id == dispute_id)
                )
                dispute = result.scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found"}

                # Get uploaded docs
                result = await db.execute(
                    select(DisputeDocument).where(DisputeDocument.dispute_id == dispute_id)
                )
                uploaded_docs = result.scalars().all()
                uploaded_types = {d.doc_type for d in uploaded_docs}

                # Get required docs for category
                category = dispute.category or "default"
                required = REQUIRED_DOCS.get(category, REQUIRED_DOCS["default"])

                missing_mandatory = []
                missing_recommended = []
                uploaded_list = []

                for req in required:
                    if req["type"] in uploaded_types:
                        uploaded_list.append(req["label"])
                    elif req["mandatory"]:
                        missing_mandatory.append(req["label"])
                    else:
                        missing_recommended.append(req["label"])

                is_complete = len(missing_mandatory) == 0

                return {
                    "dispute_id": dispute_id,
                    "category": category,
                    "is_complete": is_complete,
                    "uploaded": uploaded_list,
                    "missing_mandatory": missing_mandatory,
                    "missing_recommended": missing_recommended,
                    "total_uploaded": len(uploaded_docs),
                    "message": (
                        "All mandatory documents are uploaded."
                        if is_complete
                        else f"Missing {len(missing_mandatory)} mandatory document(s): {', '.join(missing_mandatory)}"
                    ),
                }

        except Exception as e:
            log.error(f"Missing docs check failed: {e}")
            return {"error": str(e)}
