"""Text chunking for RAG."""

import re

from src.core.logging import log


class TextChunker:
    """Split text into overlapping chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        chars_per_token: float = 4,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chars_per_token = chars_per_token
        self.chunk_chars = int(chunk_size * chars_per_token)
        self.overlap_chars = int(chunk_overlap * chars_per_token)

    def chunk_text(self, text: str, source: str = "") -> list[dict]:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []

        text = self._clean_text(text)
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_chars
            if end < len(text):
                end = self._find_break_point(text, start, end)

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "start_char": start,
                    "end_char": end,
                    "index": index,
                    "source": source,
                    "token_count": self._estimate_tokens(chunk_text),
                })
                index += 1

            start = end - self.overlap_chars
            if start <= (chunks[-1]["start_char"] if chunks else 0):
                start = end

        log.info(f"Split text into {len(chunks)} chunks (source={source})")
        return chunks

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.replace('\x00', '')
        return text.strip()

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        search_text = text[start:end]

        para_break = search_text.rfind('\n\n')
        if para_break > len(search_text) * 0.5:
            return start + para_break + 2

        for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            sent_break = search_text.rfind(punct)
            if sent_break > len(search_text) * 0.5:
                return start + sent_break + len(punct)

        newline = search_text.rfind('\n')
        if newline > len(search_text) * 0.5:
            return start + newline + 1

        space = search_text.rfind(' ')
        if space > len(search_text) * 0.7:
            return start + space + 1

        return end

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) / self.chars_per_token)
