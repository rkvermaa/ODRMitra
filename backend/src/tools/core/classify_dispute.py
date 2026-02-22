"""Classify dispute tool — categorize dispute using LLM."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class ClassifyDisputeTool(BaseTool):
    """Classify an MSME dispute into sub-categories using LLM analysis."""

    name = "classify_dispute"
    description = (
        "Classify an MSME delayed payment dispute into category and sub-category "
        "based on the case description, with confidence score and reasoning."
    )
    parameters = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Description of the dispute including facts, amounts, dates",
            },
            "claimed_amount": {
                "type": "number",
                "description": "Amount claimed in INR",
            },
        },
        "required": ["description"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        description = arguments["description"]
        claimed_amount = arguments.get("claimed_amount")

        try:
            from src.llm import get_llm_client

            llm = get_llm_client()

            prompt = f"""Analyze this MSME delayed payment dispute and classify it.

Dispute Description: {description}
{f'Claimed Amount: INR {claimed_amount:,.2f}' if claimed_amount else ''}

Classify into:
1. **Category**: One of: delayed_payment, non_payment, partial_payment, disputed_quality, contractual_dispute, other
2. **Sub-category**: More specific classification
3. **Confidence**: 0.0 to 1.0
4. **Key Issues**: List the main legal/factual issues
5. **Applicable Sections**: Relevant MSMED Act sections
6. **Reasoning**: Brief explanation

Respond in JSON format:
{{"category": "...", "sub_category": "...", "confidence": 0.X, "key_issues": ["..."], "applicable_sections": ["Section X"], "reasoning": "..."}}"""

            response = await llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            import json
            try:
                content = response.content or "{}"
                # Try to extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                result = json.loads(content.strip())
            except (json.JSONDecodeError, IndexError):
                result = {
                    "category": "delayed_payment",
                    "sub_category": "general",
                    "confidence": 0.5,
                    "reasoning": response.content or "Classification could not be parsed.",
                }

            return result

        except Exception as e:
            log.error(f"Dispute classification failed: {e}")
            return {"error": str(e)}
