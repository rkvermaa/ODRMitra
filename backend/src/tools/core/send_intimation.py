"""Send intimation tool — dispatch the Section 18 notice to the buyer."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class SendIntimationTool(BaseTool):
    """Send the Section 18 intimation notice for a case, on demand."""

    name = "send_intimation"
    description = (
        "Send the Section 18 intimation notice to the buyer/respondent of a "
        "case (WhatsApp), plus the confirmation to the seller. Call as soon as "
        "the buyer's mobile number is on the case and intimation has not been "
        "sent yet — do NOT wait for the remaining details. Reports truthfully "
        "whether the notice was actually delivered; never tell the user an "
        "intimation was sent unless this tool returned success."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the case to send the intimation for",
            },
        },
        "required": ["dispute_id"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid

        from sqlalchemy import select

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute
        from src.tasks.dispatcher import dispatch_buyer_and_seller_intimation

        dispute_id = arguments.get("dispute_id", "")
        user_id = context.get("user_id")

        try:
            async with async_session_factory() as db:
                dispute = (
                    await db.execute(
                        select(Dispute).where(
                            Dispute.id == uuid.UUID(str(dispute_id)),
                            Dispute.claimant_id == uuid.UUID(str(user_id)),
                        )
                    )
                ).scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found for this user"}
                if not dispute.respondent_mobile:
                    return {
                        "error": "No buyer mobile number on this case yet — collect it first"
                    }
                if dispute.intimation_sent_at:
                    return {
                        "already_sent": True,
                        "case_number": dispute.case_number,
                        "sent_at": dispute.intimation_sent_at.isoformat(),
                        "message": "Intimation was already delivered — do not send again unless the user explicitly asks",
                    }
                case_number = dispute.case_number

            # Run the full dispatch (buyer notice + seller confirmation) and
            # wait for it so we can report the real outcome.
            await dispatch_buyer_and_seller_intimation(
                dispute_id=str(dispute_id), user_id=str(user_id)
            )

            # Verify delivery — the dispatcher stamps intimation_sent_at only
            # on a successful buyer send.
            async with async_session_factory() as db:
                dispute = (
                    await db.execute(
                        select(Dispute).where(Dispute.id == uuid.UUID(str(dispute_id)))
                    )
                ).scalar_one_or_none()

            if dispute and dispute.intimation_sent_at:
                return {
                    "success": True,
                    "case_number": case_number,
                    "sent_at": dispute.intimation_sent_at.isoformat(),
                    "status": dispute.status,
                }
            return {
                "success": False,
                "error": (
                    "Intimation dispatch did not complete (WhatsApp bot may be "
                    "disconnected) — tell the user it could NOT be sent yet"
                ),
            }

        except (ValueError, TypeError) as e:
            return {"error": f"Invalid dispute_id: {e}"}
        except Exception as e:
            log.error(f"send_intimation failed: {e}")
            return {"error": str(e)}
