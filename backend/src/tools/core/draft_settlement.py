"""Draft settlement agreement tool."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class DraftSettlementTool(BaseTool):
    """Draft a settlement agreement based on negotiated terms."""

    name = "draft_settlement"
    description = (
        "Generate a draft settlement agreement in markdown format based on the dispute details "
        "and negotiated/agreed terms. Includes payment schedule and conditions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute",
            },
            "settlement_amount": {
                "type": "number",
                "description": "Agreed settlement amount in INR",
            },
            "payment_terms": {
                "type": "string",
                "description": "Payment terms (e.g., 'lump sum within 30 days', '3 monthly installments')",
            },
            "additional_terms": {
                "type": "string",
                "description": "Any additional terms or conditions",
            },
        },
        "required": ["dispute_id", "settlement_amount"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        dispute_id = arguments["dispute_id"]
        settlement_amount = arguments["settlement_amount"]
        payment_terms = arguments.get("payment_terms", "lump sum within 30 days")
        additional_terms = arguments.get("additional_terms", "")

        try:
            from src.db.session import async_session_factory
            from src.db.models.dispute import Dispute
            from src.db.models.settlement import SettlementAgreement, SettlementStatus
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(
                    select(Dispute).where(Dispute.id == dispute_id)
                )
                dispute = result.scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found"}

                # Generate with LLM
                from src.llm import get_llm_client
                llm = get_llm_client()

                prompt = f"""Draft a formal settlement agreement in markdown for this MSME dispute:

Case Number: {dispute.case_number}
Claimant: (from case records)
Respondent: {dispute.respondent_name}
Original Claim: INR {dispute.claimed_amount:,.2f if dispute.claimed_amount else 0}
Settlement Amount: INR {settlement_amount:,.2f}
Payment Terms: {payment_terms}
{f'Additional Terms: {additional_terms}' if additional_terms else ''}

Generate a professional settlement agreement markdown with:
1. Title and case reference
2. Parties section
3. Recitals (background of dispute)
4. Settlement terms (amount, payment schedule)
5. Release and discharge clause
6. Confidentiality clause
7. Governing law (MSMED Act 2006)
8. Signature blocks"""

                response = await llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )

                content_md = response.content or "Settlement agreement generation failed."

                # Save settlement
                settlement = SettlementAgreement(
                    dispute_id=dispute_id,
                    content_markdown=content_md,
                    settlement_amount=settlement_amount,
                    payment_schedule={"terms": payment_terms},
                    terms={"additional": additional_terms} if additional_terms else {},
                    status=SettlementStatus.DRAFT.value,
                )
                db.add(settlement)
                await db.commit()
                await db.refresh(settlement)

                return {
                    "dispute_id": dispute_id,
                    "settlement_id": str(settlement.id),
                    "settlement_amount": settlement_amount,
                    "status": "draft",
                    "content_markdown": content_md,
                }

        except Exception as e:
            log.error(f"Settlement drafting failed: {e}")
            return {"error": str(e)}
