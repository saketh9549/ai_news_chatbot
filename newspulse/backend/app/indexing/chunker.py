"""Text chunking for articles — paragraph-aware with overlap."""

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    index: int
    text: str


def chunk_text(
    text: str,
    max_chunk_size: int = 1200,
    overlap: int = 120,
) -> list[TextChunk]:
    """Split text into chunks respecting paragraph boundaries.

    Strategy: split on double newlines (paragraphs), then merge small paragraphs
    up to max_chunk_size. Add overlap from previous chunk for context continuity.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    if not paragraphs:
        # Fall back to sentence-level splitting for single-paragraph text
        paragraphs = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    if not paragraphs:
        return [TextChunk(index=0, text=text.strip())]

    chunks: list[TextChunk] = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        # If adding this paragraph exceeds max size, finalize current chunk
        if current_chunk and len(current_chunk) + len(para) + 1 > max_chunk_size:
            chunks.append(TextChunk(index=chunk_index, text=current_chunk.strip()))
            chunk_index += 1
            # Start next chunk with overlap from end of previous
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + para
            else:
                current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(TextChunk(index=chunk_index, text=current_chunk.strip()))

    return chunks
