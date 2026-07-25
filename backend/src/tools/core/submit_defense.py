"""Submit defense tool — the respondent's Statement of Defense (ODR Step 4)."""

import asyncio
from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log
from src.tools.core.lookup_cases import _norm_mobile


class SubmitDefenseTool(BaseTool):
    """Record the buyer/respondent's Statement of Defense on a dispute."""

    name = "submit_defense"
    description = (
        "File the RESPONDENT's (buyer's) Statement of Defense (SOD) on a case "
        "filed against them. Call this the moment the respondent states their "
        "side — whether they admit, partly admit, or deny the claim, and why "
        "(e.g. defective goods, already paid). Records the defense, advances "
        "the case to 'SOD filed', and notifies the seller. Only the respondent "
        "of the case may file this."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the case filed AGAINST this user (from COMPLAINTS FILED AGAINST THIS USER context)",
            },
            "response_type": {
                "type": "string",
                "enum": ["admit", "partial", "deny"],
                "description": "admit = accepts full claim; partial = accepts part; deny = rejects the claim",
            },
            "defense_statement": {
                "type": "string",
                "description": "The respondent's side in their own words (why payment was withheld, etc.)",
            },
            "admitted_amount": {
                "type": "number",
                "description": "Amount in INR the respondent agrees to pay, if partial/admit",
            },
        },
        "required": ["dispute_id", "response_type", "defense_statement"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus
        from src.db.models.user import User

        dispute_id = arguments.get("dispute_id", "")
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

                # Only the case's respondent may file the defense
                is_respondent = (
                    (dispute.respondent_id and dispute.respondent_id == user.id)
                    or (
                        dispute.respondent_mobile
                        and _norm_mobile(dispute.respondent_mobile)
                        == _norm_mobile(user.mobile_number)
                    )
                )
                if not is_respondent:
                    return {
                        "error": "Only the respondent of this case can submit a defense"
                    }

                if (dispute.buyer_objections or {}).get("sod_filed"):
                    return {
                        "error": "A Statement of Defense is already on record for this case",
                        "case_number": dispute.case_number,
                    }

                dispute.buyer_objections = {
                    "sod_filed": True,
                    "response_type": arguments["response_type"],
                    "defense_statement": arguments["defense_statement"],
                    "admitted_amount": arguments.get("admitted_amount"),
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                }
                dispute.respondent_id = user.id  # link the buyer's account
                dispute.status = DisputeStatus.SOD_FILED.value
                await db.commit()

                case_number = dispute.case_number
                claimant_id = str(dispute.claimant_id)
                log.info(f"submit_defense: SOD recorded on {case_number} by user {user.id}")

            # Notify the seller their buyer has responded
            asyncio.create_task(_notify_seller_sod_filed(claimant_id, case_number))

            return {
                "success": True,
                "case_number": case_number,
                "status": "sod_filed",
                "next_steps": (
                    "Case moves to mutual settlement (Pre-MSEFC). Both parties can "
                    "negotiate, run the AI outcome prediction, or proceed to MSEFC."
                ),
            }

        except (ValueError, TypeError) as e:
            return {"error": f"Invalid id: {e}"}
        except Exception as e:
            log.error(f"submit_defense failed: {e}")
            return {"error": str(e)}


async def _notify_seller_sod_filed(claimant_id: str, case_number: str) -> None:
    """WhatsApp the seller that the buyer filed their defense."""
    import uuid

    import httpx
    from sqlalchemy import select

    from src.config import settings
    from src.db.session import async_session_factory
    from src.db.models.user import User
    from src.tasks.dispatcher import _get_baileys_session_id, _normalize_mobile

    try:
        async with async_session_factory() as db:
            claimant = (
                await db.execute(select(User).where(User.id == uuid.UUID(claimant_id)))
            ).scalar_one_or_none()
        if not claimant or not claimant.mobile_number:
            return

        session_id = await _get_baileys_session_id()
        if not session_id:
            log.warning("No connected Baileys session — cannot notify seller of SOD")
            return

        message = (
            f"⚖️ *Update — {case_number}*\n\n"
            f"Buyer ne apna jawab (Statement of Defense) file kar diya hai.\n\n"
            f"Ab case *mutual settlement* stage mein hai — aap negotiation shuru "
            f"kar sakte hain ya AI outcome prediction dekh sakte hain. "
            f"Details ke liye yahan reply karein ya dashboard dekhein."
        )
        baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
        api_key = settings.get("baileys_api_key", "baileys-secret-key")
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{baileys_url}/sessions/{session_id}/send",
                json={"to": _normalize_mobile(claimant.mobile_number), "message": message},
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                timeout=30.0,
            )
        log.info(f"Seller notified of SOD on {case_number}")
    except Exception as e:
        log.error(f"_notify_seller_sod_filed failed: {e}")
