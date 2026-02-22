"""Lookup Cases tool — find disputes by mobile number or case number."""

from typing import Any

from sqlalchemy import select, or_

from src.tools.base import BaseTool
from src.core.logging import log


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
                # Look up by mobile number — find user first
                result = await db.execute(
                    select(User).where(User.mobile_number == mobile)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return {
                        "found": False,
                        "message": f"No user found with mobile number {mobile}.",
                        "cases": [],
                    }

                # Find disputes where user is claimant
                result = await db.execute(
                    select(Dispute).where(
                        Dispute.claimant_id == user.id
                    ).order_by(Dispute.created_at.desc())
                )
                disputes = result.scalars().all()

            if not disputes:
                return {
                    "found": False,
                    "message": "No cases found.",
                    "cases": [],
                }

            cases = []
            for d in disputes:
                cases.append({
                    "case_number": d.case_number,
                    "title": d.title,
                    "status": d.status,
                    "category": d.category,
                    "claimed_amount": float(d.claimed_amount) if d.claimed_amount else None,
                    "respondent_name": d.respondent_name,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                })

            log.info(f"lookup_cases: found {len(cases)} cases")

            return {
                "found": True,
                "total": len(cases),
                "cases": cases,
            }
