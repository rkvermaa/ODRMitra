"""Analyze document tool — extract entities from uploaded documents."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class AnalyzeDocumentTool(BaseTool):
    """Extract entities, amounts, dates from uploaded dispute documents."""

    name = "analyze_document"
    description = (
        "Analyze an uploaded document (invoice, PO, contract) and extract key entities: "
        "amounts, dates, party names, invoice numbers, terms, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "ID of the uploaded document to analyze",
            },
        },
        "required": ["document_id"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        document_id = arguments["document_id"]

        try:
            from src.db.session import async_session_factory
            from src.db.models.document import DisputeDocument, AnalysisStatus
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(
                    select(DisputeDocument).where(DisputeDocument.id == document_id)
                )
                doc = result.scalar_one_or_none()

                if not doc:
                    return {"error": f"Document {document_id} not found"}

                if doc.analysis_status == AnalysisStatus.COMPLETED.value and doc.analysis_result:
                    return {"document_id": document_id, "status": "already_analyzed", **doc.analysis_result}

                # Update status to processing
                doc.analysis_status = AnalysisStatus.PROCESSING.value
                await db.commit()

                # Parse document with LlamaParse
                try:
                    from src.rag.document_parser import parse_document
                    parsed_text = await parse_document(doc.file_url)
                except Exception as e:
                    log.warning(f"LlamaParse failed, using file directly: {e}")
                    parsed_text = f"[Document: {doc.original_filename}]"

                # Analyze with LLM
                from src.llm import get_llm_client
                llm = get_llm_client()

                prompt = f"""Analyze this document and extract all key information.

Document name: {doc.original_filename}
Document type: {doc.doc_type}

Document content:
{parsed_text[:4000]}

Extract and return JSON:
{{
    "document_type": "invoice/purchase_order/contract/other",
    "parties": {{"seller": "...", "buyer": "..."}},
    "invoice_number": "...",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "acceptance_date": "YYYY-MM-DD or null (date buyer accepted goods)",
    "total_amount": 0.00,
    "amount_received": 0.00,
    "items": [{{"description": "...", "quantity": 0, "amount": 0.00}}],
    "payment_terms": "...",
    "po_number": "... or null",
    "buyer_gstin": "... or null",
    "buyer_pan": "... or null",
    "key_dates": [{{"event": "...", "date": "YYYY-MM-DD"}}],
    "summary": "Brief summary of the document"
}}"""

                response = await llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )

                import json
                try:
                    content = response.content or "{}"
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    analysis = json.loads(content.strip())
                except (json.JSONDecodeError, IndexError):
                    analysis = {"summary": response.content, "raw_parse": True}

                # Save results
                doc.analysis_status = AnalysisStatus.COMPLETED.value
                doc.analysis_result = analysis
                if "total_amount" in analysis:
                    doc.extracted_amount = analysis["total_amount"]
                await db.commit()

                # Auto-fill: create/update Invoice record and update Dispute financials
                await self._auto_fill(db, doc, analysis)

                return {"document_id": document_id, "status": "completed", **analysis}

        except Exception as e:
            log.error(f"Document analysis failed: {e}")
            return {"error": str(e)}

    async def _auto_fill(self, db, doc, analysis: dict) -> None:
        """Create/update Invoice record from extraction and update Dispute summary fields."""
        try:
            from src.db.models.invoice import Invoice
            from src.db.models.dispute import Dispute
            from sqlalchemy import select
            from datetime import date as date_type

            def parse_date(val: str | None) -> date_type | None:
                if not val or val == "null":
                    return None
                try:
                    return date_type.fromisoformat(val)
                except (ValueError, TypeError):
                    return None

            def parse_float(val) -> float | None:
                if val is None:
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            doc_type = analysis.get("document_type", "")

            # Create Invoice record for invoice documents
            if doc_type == "invoice" or doc.doc_type == "invoice":
                invoice = Invoice(
                    dispute_id=doc.dispute_id,
                    invoice_number=analysis.get("invoice_number"),
                    invoice_date=parse_date(analysis.get("invoice_date")),
                    invoice_amount=parse_float(analysis.get("total_amount")),
                    acceptance_date=parse_date(analysis.get("acceptance_date")),
                    amount_received=parse_float(analysis.get("amount_received")),
                    balance_due=(
                        parse_float(analysis.get("total_amount", 0) or 0)
                        - parse_float(analysis.get("amount_received", 0) or 0)
                        if analysis.get("total_amount") is not None
                        else None
                    ),
                    document_id=doc.id,
                )
                db.add(invoice)

            # Update Dispute summary financial fields
            result = await db.execute(
                select(Dispute).where(Dispute.id == doc.dispute_id)
            )
            dispute = result.scalar_one_or_none()
            if dispute:
                if analysis.get("total_amount") is not None and dispute.invoice_amount is None:
                    dispute.invoice_amount = parse_float(analysis["total_amount"])
                if analysis.get("amount_received") is not None and dispute.amount_received is None:
                    dispute.amount_received = parse_float(analysis["amount_received"])
                if dispute.invoice_amount and dispute.amount_received is not None:
                    dispute.principal_amount = float(dispute.invoice_amount) - float(dispute.amount_received or 0)
                if analysis.get("po_number") and not dispute.po_number:
                    dispute.po_number = analysis["po_number"]
                if analysis.get("buyer_gstin") and not dispute.respondent_gstin:
                    dispute.respondent_gstin = analysis["buyer_gstin"]
                if analysis.get("buyer_pan") and not dispute.respondent_pan:
                    dispute.respondent_pan = analysis["buyer_pan"]

            await db.commit()
        except Exception as e:
            log.warning(f"Auto-fill from analysis failed: {e}")
