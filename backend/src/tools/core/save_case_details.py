"""Save case details tool — progressive persistence of collected case info."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log

# Dispute columns the agent may fill via collection (only empty fields are
# written — collected details never overwrite existing data).
_ALLOWED_FIELDS = (
    "respondent_name",
    "respondent_mobile",
    "respondent_email",
    "respondent_gstin",
    "respondent_state",
    "respondent_district",
    "respondent_pin_code",
    "respondent_address",
    "po_number",
    "cause_of_action",
    "goods_services_description",
)


class SaveCaseDetailsTool(BaseTool):
    """Persist details the user just provided onto their dispute — call
    IMMEDIATELY after each answer, never batch."""

    name = "save_case_details"
    description = (
        "Save case details the user just provided to the database. Call this "
        "IMMEDIATELY every time the user gives any detail for an existing case "
        "(buyer email/GSTIN/state/address, PO number, cause of action, etc.) — "
        "do NOT wait until all details are collected. Only empty fields are "
        "written; existing values are never overwritten. Set filing_complete "
        "to true once all key details are in (buyer email or GSTIN, state, PO number)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute being completed (from USER'S COMPLAINTS context)",
            },
            **{
                field: {"type": "string", "description": f"Value for {field}"}
                for field in _ALLOWED_FIELDS
            },
            "filing_complete": {
                "type": "boolean",
                "description": "true when all key details are collected — marks the case fully filed",
            },
        },
        "required": ["dispute_id"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid

        from sqlalchemy import select

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus

        dispute_id = arguments.get("dispute_id", "")
        user_id = context.get("user_id")

        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Dispute).where(
                        Dispute.id == uuid.UUID(str(dispute_id)),
                        Dispute.claimant_id == uuid.UUID(str(user_id)),
                    )
                )
                dispute = result.scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found for this user"}

                saved: list[str] = []
                skipped: list[str] = []
                for field in _ALLOWED_FIELDS:
                    value = arguments.get(field)
                    if not value:
                        continue
                    if getattr(dispute, field, None):
                        skipped.append(field)  # already set — never overwrite
                    else:
                        setattr(dispute, field, str(value).strip())
                        saved.append(field)

                if arguments.get("filing_complete"):
                    # Completion marks the case FILED — but never regress a
                    # case that already advanced (e.g. intimation_sent).
                    order = [s.value for s in DisputeStatus]
                    if order.index(dispute.status) < order.index(DisputeStatus.FILED.value):
                        dispute.status = DisputeStatus.FILED.value

                await db.commit()
                log.info(
                    f"save_case_details: {dispute.case_number} saved={saved} skipped={skipped}"
                )
                return {
                    "success": True,
                    "case_number": dispute.case_number,
                    "saved_fields": saved,
                    "already_set": skipped,
                }

        except (ValueError, TypeError) as e:
            return {"error": f"Invalid dispute_id: {e}"}
        except Exception as e:
            log.error(f"save_case_details failed: {e}")
            return {"error": str(e)}
