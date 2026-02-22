"""Background indexing service for RAG documents."""

import asyncio
import traceback
import tempfile
from pathlib import Path

import httpx

from src.core.logging import log
from src.db.session import async_session_factory
from src.rag.qdrant_search import QdrantSearch, LEGAL_COLLECTION, CASE_DOCS_COLLECTION
from src.rag.chunker import TextChunker
from src.rag.document_parser import parse_document


async def _download_file(url: str) -> str:
    """Download a file from URL to a temporary path and return the path."""
    log.info(f"[INDEX] Downloading file from: {url[:100]}...")
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    suffix = ".pdf"
    if ".doc" in url.lower():
        suffix = ".docx"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(resp.content)
    tmp.close()
    log.info(f"[INDEX] Downloaded {len(resp.content)} bytes to {tmp.name}")
    return tmp.name


def fire_and_forget(coro):
    """Launch an async coroutine as a fire-and-forget task with error logging."""
    async def _wrapper():
        try:
            await coro
        except Exception as e:
            log.error(f"[INDEX] Background task failed: {e}")
            log.error(f"[INDEX] Traceback: {traceback.format_exc()}")

    loop = asyncio.get_event_loop()
    loop.create_task(_wrapper())


async def index_knowledge_document(doc_id: str) -> None:
    """Index a KnowledgeDocument into the odrmitra_legal collection."""
    from src.db.models.knowledge_document import KnowledgeDocument, IndexStatus

    log.info(f"[INDEX] Starting indexing for KnowledgeDocument {doc_id}")

    async with async_session_factory() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                log.error(f"[INDEX] KnowledgeDocument {doc_id} not found in DB")
                return

            # Mark as indexing
            doc.index_status = IndexStatus.INDEXING.value
            doc.index_error = None
            await db.commit()
            log.info(f"[INDEX] Marked {doc.original_filename} as indexing")

            # Download file
            tmp_path = await _download_file(doc.file_url)

            try:
                # Parse document
                log.info(f"[INDEX] Parsing {doc.original_filename}...")
                text = await parse_document(tmp_path)
                log.info(f"[INDEX] Parsed: {len(text)} chars")

                if not text or text.startswith("["):
                    raise ValueError(f"Failed to parse document: {text[:200]}")

                # Chunk
                chunker = TextChunker(chunk_size=400, chunk_overlap=50)
                chunks = chunker.chunk_text(text, source=doc.original_filename)
                log.info(f"[INDEX] Generated {len(chunks)} chunks")

                if not chunks:
                    raise ValueError("No chunks generated from document")

                # Delete existing chunks for this source (in case of re-index)
                QdrantSearch.delete_by_source(
                    doc.original_filename,
                    collection_name=LEGAL_COLLECTION,
                )

                # Index into Qdrant
                count = QdrantSearch.index_chunks(
                    chunks,
                    source=doc.original_filename,
                    collection_name=LEGAL_COLLECTION,
                    extra_payload={"doc_id": str(doc.id)},
                )

                # Update status
                doc.index_status = IndexStatus.INDEXED.value
                doc.chunk_count = count
                doc.index_error = None
                await db.commit()

                log.info(f"[INDEX] SUCCESS: Indexed {count} chunks for {doc.original_filename}")

            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            log.error(f"[INDEX] FAILED to index KnowledgeDocument {doc_id}: {e}")
            log.error(f"[INDEX] Traceback: {traceback.format_exc()}")
            try:
                doc.index_status = IndexStatus.FAILED.value
                doc.index_error = str(e)[:500]
                await db.commit()
            except Exception as commit_err:
                log.error(f"[INDEX] Failed to update status: {commit_err}")


async def index_case_document(doc_id: str, dispute_id: str) -> None:
    """Index a DisputeDocument into the odrmitra_case_docs collection."""
    from src.db.models.document import DisputeDocument

    log.info(f"[INDEX] Starting case doc indexing: doc={doc_id} dispute={dispute_id}")

    async with async_session_factory() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(DisputeDocument).where(DisputeDocument.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                log.error(f"[INDEX] DisputeDocument {doc_id} not found")
                return

            doc.index_status = "indexing"
            await db.commit()

            tmp_path = await _download_file(doc.file_url)

            try:
                text = await parse_document(tmp_path)
                if not text or text.startswith("["):
                    raise ValueError(f"Failed to parse document: {text[:200]}")

                chunker = TextChunker(chunk_size=400, chunk_overlap=50)
                chunks = chunker.chunk_text(text, source=doc.original_filename)

                if not chunks:
                    raise ValueError("No chunks generated from document")

                QdrantSearch.delete_by_filter(
                    CASE_DOCS_COLLECTION,
                    {"doc_id": str(doc.id)},
                )

                count = QdrantSearch.index_chunks(
                    chunks,
                    source=doc.original_filename,
                    collection_name=CASE_DOCS_COLLECTION,
                    extra_payload={
                        "dispute_id": dispute_id,
                        "doc_id": str(doc.id),
                        "doc_type": doc.doc_type,
                        "uploaded_by": str(doc.uploaded_by),
                    },
                )

                doc.index_status = "indexed"
                await db.commit()
                log.info(f"[INDEX] SUCCESS: Indexed {count} case doc chunks for dispute {dispute_id}")

            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            log.error(f"[INDEX] FAILED case document {doc_id}: {e}")
            log.error(f"[INDEX] Traceback: {traceback.format_exc()}")
            try:
                doc.index_status = "failed"
                await db.commit()
            except Exception:
                pass


async def delete_knowledge_document_chunks(doc_id: str, source: str) -> None:
    """Delete all chunks for a knowledge document from Qdrant."""
    try:
        QdrantSearch.delete_by_filter(
            LEGAL_COLLECTION,
            {"doc_id": doc_id},
        )
        log.info(f"[INDEX] Deleted chunks for knowledge doc {source}")
    except Exception as e:
        log.error(f"[INDEX] Failed to delete chunks for {source}: {e}")
