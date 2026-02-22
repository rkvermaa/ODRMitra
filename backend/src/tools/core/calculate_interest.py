"""Calculate interest tool — Section 16 MSMED Act 2006."""

from datetime import date, datetime
from typing import Any

from src.tools.base import BaseTool
from src.config import settings


class CalculateInterestTool(BaseTool):
    """Calculate compound interest per Section 16 of MSMED Act 2006.

    Interest = 3x RBI bank rate, compounded monthly.
    """

    name = "calculate_interest"
    description = (
        "Calculate statutory interest on delayed MSME payments under Section 16 of MSMED Act 2006. "
        "Interest rate is 3 times the RBI bank rate, compounded monthly with monthly rests."
    )
    parameters = {
        "type": "object",
        "properties": {
            "principal_amount": {
                "type": "number",
                "description": "Outstanding principal amount in INR",
            },
            "due_date": {
                "type": "string",
                "description": "Payment due date (YYYY-MM-DD)",
            },
            "calculation_date": {
                "type": "string",
                "description": "Date to calculate interest up to (YYYY-MM-DD). Defaults to today.",
            },
        },
        "required": ["principal_amount", "due_date"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        principal = arguments["principal_amount"]
        due_date = datetime.strptime(arguments["due_date"], "%Y-%m-%d").date()

        calc_date_str = arguments.get("calculation_date")
        calc_date = (
            datetime.strptime(calc_date_str, "%Y-%m-%d").date()
            if calc_date_str
            else date.today()
        )

        if calc_date <= due_date:
            return {
                "principal": principal,
                "interest": 0,
                "total": principal,
                "days_overdue": 0,
                "message": "Payment is not yet overdue.",
            }

        # Section 16: Interest = 3x bank rate, compounded monthly
        bank_rate = float(settings.get("RBI_BANK_RATE", 6.50))
        annual_rate = bank_rate * 3  # 3x bank rate
        monthly_rate = annual_rate / 12 / 100

        # Calculate months between dates
        days_overdue = (calc_date - due_date).days
        months = days_overdue / 30.44  # Average days per month

        # Compound monthly: A = P(1 + r)^n
        total = principal * ((1 + monthly_rate) ** months)
        interest = total - principal

        return {
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "total": round(total, 2),
            "days_overdue": days_overdue,
            "months_overdue": round(months, 1),
            "rbi_bank_rate": bank_rate,
            "applicable_rate": annual_rate,
            "monthly_rate": round(monthly_rate * 100, 4),
            "calculation_date": calc_date.isoformat(),
            "due_date": due_date.isoformat(),
            "statutory_basis": (
                f"Section 16, MSMED Act 2006: Interest at 3x RBI bank rate "
                f"({bank_rate}% × 3 = {annual_rate}% p.a.) compounded monthly."
            ),
        }
