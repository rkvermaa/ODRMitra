"""Finalize settlement tool — both parties agreed; draft and deliver to both."""

import asyncio
from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log
from src.tools.core.lookup_cases import _norm_mobile


class FinalizeSettlementTool(BaseTool):
    """Draft the agreed settlement and send it to both parties on WhatsApp."""

    name = "finalize_settlement"
    description = (
        "Call ONLY when BOTH parties have agreed on a settlement amount (the "
        "other side's explicit agreement must be on record in the conversation "
        "or the case — never finalize on one party's wish alone). Drafts the "
        "formal settlement agreement, saves it against the case, marks the "
        "dispute resolved, and sends the settlement summary to BOTH the seller "
        "and the buyer on WhatsApp."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute being settled",
            },
            "settlement_amount": {
                "type": "number",
                "description": "The amount in INR both parties agreed on",
            },
            "payment_terms": {
                "type": "string",
                "description": "Agreed payment terms (e.g. 'lump sum within 15 days', '2 monthly installments')",
            },
            "additional_terms": {
                "type": "string",
                "description": "Any other agreed conditions",
            },
        },
        "required": ["dispute_id", "settlement_amount"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid

        from sqlalchemy import select

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus
        from src.db.models.settlement import SettlementAgreement, SettlementStatus
        from src.db.models.user import User
        from src.tools.core.draft_settlement import DraftSettlementTool

        dispute_id = arguments["dispute_id"]
        amount = float(arguments["settlement_amount"])
        payment_terms = arguments.get("payment_terms", "lump sum within 30 days")
        user_id = context.get("user_id")

        try:
            async with async_session_factory() as db:
                dispute = (
                    await db.execute(
                        select(Dispute).where(Dispute.id == uuid.UUID(str(dispute_id)))
                    )
                ).scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found"}

                user = (
                    await db.execute(
                        select(User).where(User.id == uuid.UUID(str(user_id)))
                    )
                ).scalar_one_or_none()
                if not user:
                    return {"error": "User not found"}

                # Only a party to the case may finalize its settlement
                is_claimant = dispute.claimant_id == user.id
                is_respondent = (
                    (dispute.respondent_id and dispute.respondent_id == user.id)
                    or (
                        dispute.respondent_mobile
                        and _norm_mobile(dispute.respondent_mobile)
                        == _norm_mobile(user.mobile_number)
                    )
                )
                if not (is_claimant or is_respondent):
                    return {"error": "Only a party to this case can finalize its settlement"}

                claimant = (
                    await db.execute(
                        select(User).where(User.id == dispute.claimant_id)
                    )
                ).scalar_one_or_none()
                case_number = dispute.case_number
                claimant_name = claimant.name if claimant else "Claimant"
                claimant_mobile = claimant.mobile_number if claimant else None
                respondent_name = dispute.respondent_name or "Respondent"
                respondent_mobile = dispute.respondent_mobile

            # Draft the formal agreement (reuses the drafting tool + LLM)
            draft = await DraftSettlementTool().execute(
                {
                    "dispute_id": dispute_id,
                    "settlement_amount": amount,
                    "payment_terms": payment_terms,
                    "additional_terms": arguments.get("additional_terms", ""),
                },
                context,
            )
            if draft.get("error"):
                return {"error": f"Agreement drafting failed: {draft['error']}"}

            # Mark the settlement accepted and the case resolved
            async with async_session_factory() as db:
                settlement = (
                    await db.execute(
                        select(SettlementAgreement).where(
                            SettlementAgreement.id == uuid.UUID(draft["settlement_id"])
                        )
                    )
                ).scalar_one_or_none()
                if settlement:
                    settlement.status = SettlementStatus.EXECUTED.value
                dispute = (
                    await db.execute(
                        select(Dispute).where(Dispute.id == uuid.UUID(str(dispute_id)))
                    )
                ).scalar_one_or_none()
                if dispute:
                    dispute.status = DisputeStatus.RESOLUTION.value
                await db.commit()

            # Deliver the settlement summary to BOTH parties
            summary = (
                f"⚖️ *Settlement Agreement — {case_number}*\n\n"
                f"Dono parties ki sehmati se case settle ho gaya hai. ✅\n\n"
                f"*Seller:* {claimant_name}\n"
                f"*Buyer:* {respondent_name}\n"
                f"*Settlement Amount:* ₹{amount:,.2f}\n"
                f"*Payment Terms:* {payment_terms}\n\n"
                f"Poora agreement dashboard par uplabdh hai — dono parties "
                f"review karke sign kar sakti hain.\n\n"
                f"— ODRMitra (ओडीआर मित्र)"
            )
            for mobile in (claimant_mobile, respondent_mobile):
                if mobile:
                    asyncio.create_task(_send_whatsapp(mobile, summary))

            log.info(f"finalize_settlement: {case_number} settled at ₹{amount:,.0f}")
            return {
                "success": True,
                "case_number": case_number,
                "settlement_amount": amount,
                "payment_terms": payment_terms,
                "status": "resolved",
                "sent_to": [m for m in (claimant_mobile, respondent_mobile) if m],
                "agreement_preview": (draft.get("content_markdown") or "")[:400],
            }

        except (ValueError, TypeError) as e:
            return {"error": f"Invalid input: {e}"}
        except Exception as e:
            log.error(f"finalize_settlement failed: {e}")
            return {"error": str(e)}


async def _send_whatsapp(mobile: str, message: str) -> None:
    """Send a message via the connected bot (best-effort)."""
    import httpx

    from src.config import settings
    from src.tasks.dispatcher import _get_baileys_session_id, _normalize_mobile

    try:
        session_id = await _get_baileys_session_id()
        if not session_id:
            log.warning("finalize_settlement: no connected bot — WhatsApp copy not sent")
            return
        baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
        api_key = settings.get("baileys_api_key", "baileys-secret-key")
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{baileys_url}/sessions/{session_id}/send",
                json={"to": _normalize_mobile(mobile), "message": message},
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                timeout=30.0,
            )
        log.info(f"Settlement summary sent to {mobile}")
    except Exception as e:
        log.error(f"Settlement WhatsApp send failed for {mobile}: {e}")
