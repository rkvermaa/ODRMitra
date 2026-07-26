"""Relay settlement offer tool — carry one party's offer to the other's phone."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log
from src.tools.core.lookup_cases import _norm_mobile


class RelaySettlementOfferTool(BaseTool):
    """Record a party's settlement offer and deliver it to the counterparty on WhatsApp."""

    name = "relay_settlement_offer"
    description = (
        "Call when ONE party states a settlement offer or counter-offer amount "
        "for a case (and the other side has not yet agreed). Records the offer "
        "as a negotiation round and delivers it to the OTHER party on WhatsApp "
        "with instructions to accept or counter. Never ask a party to convey "
        "an offer themselves — use this tool. Do NOT use this to finalize; "
        "call finalize_settlement only after both sides agree."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute the offer belongs to",
            },
            "offer_amount": {
                "type": "number",
                "description": "The settlement amount in INR being offered",
            },
            "payment_terms": {
                "type": "string",
                "description": "Proposed payment terms, if the party stated any (e.g. 'lump sum within 15 days')",
            },
            "note": {
                "type": "string",
                "description": "Optional short message from the offering party to pass along",
            },
        },
        "required": ["dispute_id", "offer_amount"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        import uuid

        from sqlalchemy import func, select

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute
        from src.db.models.negotiation import NegotiationRound
        from src.db.models.user import User
        from src.tools.core.finalize_settlement import _send_whatsapp

        dispute_id = arguments["dispute_id"]
        amount = float(arguments["offer_amount"])
        payment_terms = arguments.get("payment_terms")
        note = arguments.get("note")
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

                # Only a party to the case may make an offer on it
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
                    return {"error": "Only a party to this case can make a settlement offer"}

                claimant = (
                    await db.execute(
                        select(User).where(User.id == dispute.claimant_id)
                    )
                ).scalar_one_or_none()

                if is_claimant:
                    sender_name = claimant.name if claimant else "Seller"
                    recipient_name = dispute.respondent_name or "Buyer"
                    recipient_mobile = dispute.respondent_mobile
                else:
                    sender_name = dispute.respondent_name or user.name
                    recipient_name = claimant.name if claimant else "Seller"
                    recipient_mobile = claimant.mobile_number if claimant else None

                if not recipient_mobile:
                    return {
                        "error": "The other party's mobile number is not on record — "
                        "the offer cannot be delivered"
                    }

                last_round = (
                    await db.execute(
                        select(func.max(NegotiationRound.round_number)).where(
                            NegotiationRound.dispute_id == dispute.id
                        )
                    )
                ).scalar_one()
                round_number = (last_round or 0) + 1
                db.add(
                    NegotiationRound(
                        dispute_id=dispute.id,
                        round_number=round_number,
                        claimant_offer=amount if is_claimant else None,
                        respondent_offer=None if is_claimant else amount,
                    )
                )
                await db.commit()
                case_number = dispute.case_number

            lines = [
                f"🤝 *Settlement Offer — {case_number}*\n",
                f"{sender_name} ne aapke case mein settlement offer diya hai:\n",
                f"*Offer Amount:* ₹{amount:,.2f}",
            ]
            if payment_terms:
                lines.append(f"*Payment Terms:* {payment_terms}")
            if note:
                lines.append(f"*Message:* {note}")
            lines.append(
                "\nAgar aap is offer se sehmat hain, toh isi number par reply "
                "karein — main turant formal settlement agreement draft karke "
                "dono parties ko bhej dunga. Aap counter-offer bhi de sakte hain."
            )
            lines.append("\n— ODRMitra (ओडीआर मित्र)")

            delivered = await _send_whatsapp(recipient_mobile, "\n".join(lines))
            if not delivered:
                return {
                    "error": f"Offer recorded (round {round_number}) but WhatsApp "
                    f"delivery to {recipient_name} failed — tell the user honestly"
                }

            log.info(
                f"relay_settlement_offer: {case_number} round {round_number} — "
                f"₹{amount:,.0f} relayed to {recipient_mobile}"
            )
            return {
                "success": True,
                "case_number": case_number,
                "round_number": round_number,
                "offer_amount": amount,
                "offered_by": sender_name,
                "delivered_to": recipient_name,
                "note": "The other party has been asked to accept or counter on WhatsApp",
            }

        except (ValueError, TypeError) as e:
            return {"error": f"Invalid input: {e}"}
        except Exception as e:
            log.error(f"relay_settlement_offer failed: {e}")
            return {"error": str(e)}
