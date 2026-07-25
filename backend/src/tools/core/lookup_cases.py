"""Lookup Cases tool — find disputes by mobile number or case number."""

from typing import Any

from sqlalchemy import select, or_

from src.tools.base import BaseTool
from src.core.logging import log


def _norm_mobile(number: str | None) -> str:
    """Strip '+' and a leading 91 country code for comparison."""
    digits = (number or "").lstrip("+")
    return digits[2:] if digits.startswith("91") and len(digits) == 12 else digits


class LookupCasesTool(BaseTool):
    """Look up existing disputes for a user by mobile number or case number."""

    name = "lookup_cases"
    description = "Look up existing disputes for a user by mobile number or case number. Returns list of cases with status."

    parameters = {
        "type": "object",
        "properties": {
            "mobile_number": {
                "type": "string",
                "description": "The user's registered mobile number (10 digits)",
            },
            "case_number": {
                "type": "string",
                "description": "The case number (e.g., ODR-2026-0001)",
            },
        },
        "required": [],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> Any:
        """Look up disputes by mobile number or case number."""
        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute
        from src.db.models.user import User

        mobile = arguments.get("mobile_number", "").strip()
        case_number = arguments.get("case_number", "").strip()

        if not mobile and not case_number:
            return {"error": "Please provide either a mobile number or case number."}

        async with async_session_factory() as db:
            if case_number:
                # Look up by case number
                result = await db.execute(
                    select(Dispute).where(Dispute.case_number == case_number)
                )
                disputes = result.scalars().all()
            else:
                # Both directions: cases this number FILED (as claimant) and
                # cases filed AGAINST this number (as respondent). Respondents
                # are often not registered users, so match respondent_mobile
                # directly, with and without the 91 country code.
                variants = {mobile}
                if mobile.startswith("91") and len(mobile) == 12:
                    variants.add(mobile[2:])
                elif len(mobile) == 10:
                    variants.add(f"91{mobile}")

                result = await db.execute(
                    select(User).where(User.mobile_number.in_(variants))
                )
                user = result.scalar_one_or_none()

                conditions = [Dispute.respondent_mobile.in_(variants)]
                if user:
                    conditions.append(Dispute.claimant_id == user.id)

                result = await db.execute(
                    select(Dispute)
                    .where(or_(*conditions))
                    .order_by(Dispute.created_at.desc())
                )
                disputes = result.scalars().all()

            if not disputes:
                return {
                    "found": False,
                    "message": "No cases found.",
                    "cases": [],
                }

            from src.agent.context.loader import STATUS_LABELS

            cases = []
            for d in disputes:
                # Which side of the case is this number on?
                is_respondent = bool(
                    mobile and d.respondent_mobile
                    and _norm_mobile(d.respondent_mobile) == _norm_mobile(mobile)
                    and not (user and d.claimant_id == user.id)
                )
                cases.append({
                    "case_number": d.case_number,
                    "title": d.title,
                    # Human-readable stage — the raw code invites the LLM to
                    # invent expansions ("dgp" != "Document Gathering Phase").
                    "status": STATUS_LABELS.get(d.status, d.status),
                    "category": d.category,
                    "claimed_amount": float(d.claimed_amount) if d.claimed_amount else None,
                    "respondent_name": d.respondent_name,
                    "role_of_this_user": "respondent (complaint is AGAINST them)" if is_respondent else "claimant (they filed it)",
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                })

            log.info(f"lookup_cases: found {len(cases)} cases")

            return {
                "found": True,
                "total": len(cases),
                "cases": cases,
            }
