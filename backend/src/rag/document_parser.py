"""Document parser using LlamaParse."""

import os
from pathlib import Path

from src.config import settings
from src.core.logging import log


async def parse_document(file_path: str) -> str:
    """Parse a document (PDF/image) using LlamaParse.

    Args:
        file_path: Path to the file (local path or URL).

    Returns:
        Parsed text/markdown content.
    """
    api_key = settings.get("LLAMA_CLOUD_API_KEY", "")
    if not api_key:
        log.warning("LlamaParse API key not configured, falling back to pypdf")
        return _fallback_parse(file_path)

    try:
        from llama_parse import LlamaParse

        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            language="en",
        )

        # Parse the document
        documents = await parser.aload_data(file_path)

        if not documents:
            log.warning(f"LlamaParse returned no content for {file_path}")
            return _fallback_parse(file_path)

        # Combine all pages
        text = "\n\n".join(doc.text for doc in documents if doc.text)
        log.info(f"Parsed {file_path}: {len(text)} chars via LlamaParse")
        return text

    except Exception as e:
        log.error(f"LlamaParse failed for {file_path}: {e}")
        return _fallback_parse(file_path)


def _fallback_parse(file_path: str) -> str:
    """Fallback PDF parser using pypdf."""
    try:
        from pypdf import PdfReader

        if not Path(file_path).exists():
            return f"[File not found: {file_path}]"

        reader = PdfReader(file_path)
        text = "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        log.info(f"Parsed {file_path}: {len(text)} chars via pypdf fallback")
        return text

    except Exception as e:
        log.error(f"Fallback parse failed for {file_path}: {e}")
        return f"[Failed to parse document: {e}]"


def parse_document_sync(file_path: str) -> str:
    """Synchronous version for indexing scripts."""
    api_key = settings.get("LLAMA_CLOUD_API_KEY", "")

    if api_key:
        try:
            from llama_parse import LlamaParse

            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                language="en",
            )
            documents = parser.load_data(file_path)
            if documents:
                text = "\n\n".join(doc.text for doc in documents if doc.text)
                log.info(f"Parsed {file_path}: {len(text)} chars via LlamaParse")
                return text
        except Exception as e:
            log.error(f"LlamaParse sync failed: {e}")

    return _fallback_parse(file_path)
