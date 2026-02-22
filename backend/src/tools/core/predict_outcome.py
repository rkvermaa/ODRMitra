"""Predict outcome tool — DGP outcome prediction using LLM."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class PredictOutcomeTool(BaseTool):
    """Predict probable outcome of a dispute for Digital Guided Pathway (DGP)."""

    name = "predict_outcome"
    description = (
        "Predict the probable outcome of an MSME delayed payment dispute based on case details, "
        "statutory provisions, and precedents. Used in the Digital Guided Pathway (Phase 1) "
        "to help parties assess settlement options."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dispute_id": {
                "type": "string",
                "description": "ID of the dispute to predict outcome for",
            },
        },
        "required": ["dispute_id"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        dispute_id = arguments["dispute_id"]

        try:
            from src.db.session import async_session_factory
            from src.db.models.dispute import Dispute
            from src.db.models.document import DisputeDocument
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(
                    select(Dispute).where(Dispute.id == dispute_id)
                )
                dispute = result.scalar_one_or_none()
                if not dispute:
                    return {"error": f"Dispute {dispute_id} not found"}

                # Get documents
                docs_result = await db.execute(
                    select(DisputeDocument).where(DisputeDocument.dispute_id == dispute_id)
                )
                docs = docs_result.scalars().all()

                # Build case summary
                case_summary = f"""
Case Number: {dispute.case_number}
Category: {dispute.category}
Claimed Amount: INR {dispute.claimed_amount:,.2f} if dispute.claimed_amount else 'Not specified'
Invoice Date: {dispute.invoice_date}
Due Date: {dispute.due_date}
Description: {dispute.description}
Goods/Services: {dispute.goods_services_description}
Documents Uploaded: {len(docs)}
Document Types: {', '.join(d.doc_type for d in docs)}
"""

                # Search knowledge base for precedents
                try:
                    from src.rag.qdrant_search import QdrantSearch
                    rag_context = QdrantSearch.search(
                        query=f"delayed payment dispute outcome {dispute.category} MSMED Act",
                        limit=3,
                    )
                    precedent_text = "\n".join(r["content"] for r in rag_context) if rag_context else ""
                except Exception:
                    precedent_text = ""

                # Predict with LLM
                from src.llm import get_llm_client
                llm = get_llm_client()

                prompt = f"""You are an ODR legal analysis AI. Analyze this MSME delayed payment dispute and predict the probable outcome.

{case_summary}

{f'Relevant Legal Context:{chr(10)}{precedent_text}' if precedent_text else ''}

Predict outcome considering:
1. MSMED Act 2006 provisions (Section 15-18)
2. Strength of documentation
3. Category of dispute
4. Amount and timeline

Respond in JSON:
{{
    "probable_outcome": "in_favor_of_claimant / partial_recovery / needs_more_evidence / likely_dismissed",
    "confidence": 0.X,
    "likely_recovery_percentage": 0-100,
    "statutory_interest_applicable": true/false,
    "estimated_settlement_range": {{"min": 0, "max": 0}},
    "strengths": ["..."],
    "weaknesses": ["..."],
    "recommendations": ["..."],
    "statutory_basis": "Relevant MSMED Act sections",
    "reasoning": "Detailed reasoning"
}}"""

                response = await llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )

                import json
                try:
                    content = response.content or "{}"
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    prediction = json.loads(content.strip())
                except (json.JSONDecodeError, IndexError):
                    prediction = {"reasoning": response.content, "confidence": 0.5}

                # Save to dispute
                dispute.ai_outcome_prediction = prediction
                await db.commit()

                return {"dispute_id": dispute_id, **prediction}

        except Exception as e:
            log.error(f"Outcome prediction failed: {e}")
            return {"error": str(e)}
