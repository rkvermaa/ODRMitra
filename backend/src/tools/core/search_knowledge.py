"""Search knowledge base tool — RAG search on legal documents and case documents."""

from typing import Any

from src.tools.base import BaseTool
from src.core.logging import log


class SearchKnowledgeTool(BaseTool):
    """RAG search on the legal knowledge base and case documents."""

    name = "search_knowledge"
    description = (
        "Search the legal knowledge base for information about MSMED Act, MSEFC rules, "
        "court judgments, ODR procedures, and delayed payment provisions. "
        "Can also search case-specific documents (invoices, POs, contracts) when a dispute is active. "
        "Use when you need specific legal text, precedent, or case document details."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for the knowledge base",
            },
            "collection": {
                "type": "string",
                "enum": ["legal", "case_docs", "both"],
                "description": "Which collection to search: 'legal' for laws/judgments, 'case_docs' for dispute documents, 'both' for combined search (default: legal)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 5)",
            },
        },
        "required": ["query"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        query = arguments["query"]
        limit = arguments.get("limit", 5)
        collection = arguments.get("collection", "legal")

        try:
            from src.rag.qdrant_search import QdrantSearch, LEGAL_COLLECTION, CASE_DOCS_COLLECTION

            all_results = []

            # Search legal collection
            if collection in ("legal", "both"):
                legal_results = QdrantSearch.search(
                    query=query,
                    collection_name=LEGAL_COLLECTION,
                    limit=limit,
                )
                for r in legal_results:
                    r["collection"] = "legal"
                all_results.extend(legal_results)

            # Search case docs collection (if dispute context exists)
            if collection in ("case_docs", "both"):
                dispute_id = context.get("dispute_id")
                filters = {"dispute_id": dispute_id} if dispute_id else None

                case_results = QdrantSearch.search(
                    query=query,
                    collection_name=CASE_DOCS_COLLECTION,
                    limit=limit,
                    filters=filters,
                )
                for r in case_results:
                    r["collection"] = "case_docs"
                all_results.extend(case_results)

            if not all_results:
                return {
                    "query": query,
                    "results": [],
                    "message": "No relevant documents found in the knowledge base.",
                }

            # Sort by score and limit
            all_results.sort(key=lambda r: r["score"], reverse=True)
            all_results = all_results[:limit]

            return {
                "query": query,
                "results": [
                    {
                        "content": r["content"],
                        "score": r["score"],
                        "source": r.get("source", ""),
                        "collection": r.get("collection", "legal"),
                    }
                    for r in all_results
                ],
            }
        except Exception as e:
            log.error(f"Knowledge search failed: {e}")
            return {"query": query, "error": str(e)}
