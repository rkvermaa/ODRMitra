"""Index legal documents into Qdrant."""

import sys
from pathlib import Path

from src.core.logging import log
from src.rag.chunker import TextChunker
from src.rag.qdrant_search import QdrantSearch
from src.rag.document_parser import parse_document_sync


def index_legal_documents(docs_dir: str | Path) -> dict:
    """Index all PDFs from the rag-index directory into Qdrant.

    Args:
        docs_dir: Path to directory containing PDFs.

    Returns:
        Stats dict with counts.
    """
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        log.error(f"Documents directory not found: {docs_dir}")
        return {"error": "Directory not found"}

    chunker = TextChunker(chunk_size=500, chunk_overlap=75)
    total_chunks = 0
    indexed_files = []

    pdf_files = list(docs_dir.glob("*.pdf"))
    log.info(f"Found {len(pdf_files)} PDFs to index in {docs_dir}")

    for pdf_path in pdf_files:
        source_name = pdf_path.stem
        log.info(f"Parsing: {pdf_path.name}")

        try:
            text = parse_document_sync(str(pdf_path))
            if not text or len(text) < 50:
                log.warning(f"Skipping {pdf_path.name}: too little text ({len(text)} chars)")
                continue

            chunks = chunker.chunk_text(text, source=source_name)
            if not chunks:
                log.warning(f"Skipping {pdf_path.name}: no chunks generated")
                continue

            count = QdrantSearch.index_chunks(chunks, source=source_name)
            total_chunks += count
            indexed_files.append({"file": pdf_path.name, "chunks": count, "chars": len(text)})
            log.info(f"Indexed {pdf_path.name}: {count} chunks, {len(text)} chars")

        except Exception as e:
            log.error(f"Failed to index {pdf_path.name}: {e}")
            indexed_files.append({"file": pdf_path.name, "chunks": 0, "error": str(e)})

    result = {
        "total_files": len(pdf_files),
        "indexed_files": len([f for f in indexed_files if f.get("chunks", 0) > 0]),
        "total_chunks": total_chunks,
        "files": indexed_files,
    }
    log.info(f"Indexing complete: {result['indexed_files']}/{result['total_files']} files, {total_chunks} chunks")
    return result


if __name__ == "__main__":
    """Run as: uv run python -m src.rag.indexer"""
    # Default to odr-docs/rag-index/
    docs_dir = Path(__file__).parent.parent.parent.parent / "odr-docs" / "rag-index"
    if len(sys.argv) > 1:
        docs_dir = Path(sys.argv[1])

    from src.core.logging import setup_logging
    setup_logging(debug=True)

    result = index_legal_documents(docs_dir)
    print(f"\nIndexing Results:")
    for f in result.get("files", []):
        status = f"✓ {f['chunks']} chunks" if f.get("chunks") else f"✗ {f.get('error', 'no content')}"
        print(f"  {f['file']:40s} {status}")
    print(f"\nTotal: {result['total_chunks']} chunks from {result['indexed_files']} files")
