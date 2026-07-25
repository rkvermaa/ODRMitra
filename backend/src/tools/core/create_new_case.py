"""Create new case tool — file a fresh dispute from collected details."""

import asyncio
from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class CreateNewCaseTool(BaseTool):
    """Create a new dispute once the filing conversation has the basics."""

    name = "create_new_case"
    description = (
        "File a NEW delayed-payment complaint for the current user once you "
        "have collected at least the buyer/respondent name, what was supplied, "
        "and the invoice amount. Creates the case, sends the Section 18 "
        "intimation notice to the buyer (if their mobile was provided), and "
        "returns the case number to share with the user."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short case title, e.g. 'Payment dispute - <seller name>'",
            },
            "respondent_name": {
                "type": "string",
                "description": "Buyer/respondent person or company name",
            },
            "respondent_company": {
                "type": "string",
                "description": "Buyer company name if given separately from the person",
            },
            "respondent_mobile": {
                "type": "string",
                "description": "Buyer's 10-digit mobile number (no country code)",
            },
            "goods_services_description": {
                "type": "string",
                "description": "What goods or services were supplied",
            },
            "invoice_amount": {
                "type": "number",
                "description": "Invoice amount in INR as a number",
            },
        },
        "required": ["respondent_name"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus
        from src.api.routes.disputes import _generate_case_number

        user_id = context.get("user_id")

        person = (arguments.get("respondent_name") or "").strip()
        company = (arguments.get("respondent_company") or "").strip()
        respondent_name = f"{person} ({company})" if person and company else (person or company)

        try:
            async with async_session_factory() as db:
                dispute = Dispute(
                    claimant_id=uuid.UUID(str(user_id)),
                    case_number=await _generate_case_number(db),
                    title=arguments.get("title") or "MSME Payment Dispute",
                    category="delayed_payment",
                    respondent_name=respondent_name,
                    respondent_mobile=arguments.get("respondent_mobile"),
                    goods_services_description=arguments.get("goods_services_description"),
                    status=DisputeStatus.FILED.value,
                )
                amount = arguments.get("invoice_amount")
                if amount:
                    try:
                        dispute.invoice_amount = float(amount)
                        dispute.claimed_amount = float(amount)
                    except (ValueError, TypeError):
                        pass

                db.add(dispute)
                await db.flush()
                await db.refresh(dispute)
                await db.commit()

                dispute_id = str(dispute.id)
                case_number = dispute.case_number
                log.info(f"create_new_case: {case_number} created for user {user_id}")

            # Step 3 intimation: buyer notice + seller follow-up
            if arguments.get("respondent_mobile"):
                from src.tasks.dispatcher import dispatch_buyer_and_seller_intimation

                asyncio.create_task(
                    dispatch_buyer_and_seller_intimation(
                        dispute_id=dispute_id, user_id=str(user_id)
                    )
                )

            return {
                "success": True,
                "case_number": case_number,
                "dispute_id": dispute_id,
                "intimation_dispatched": bool(arguments.get("respondent_mobile")),
            }

        except Exception as e:
            log.error(f"create_new_case failed: {e}")
            return {"error": str(e)}
