"""Prompt assembly with citation-tagged context chunks and metadata."""

from dataclasses import dataclass

from app.retrieval.hybrid_search import SearchResult


@dataclass
class CitationSource:
    index: int
    article_id: str
    source: str
    url: str
    published_at: str | None
    title: str = ""
    image_url: str | None = None
    summary: str | None = None


SYSTEM_PROMPT = """You are NewsPulse, an elite AI news intelligence assistant. Your mission is to provide an executive, structured, and strictly source-grounded news briefing based on the provided source articles.

Follow these rules strictly:
1. EXECUTIVE SYNTHESIS: Start with a crisp overview paragraph synthesizing the core situation. Follow with structured bullet points breaking down the most crucial developments, figures, decisions, and market implications.
2. STRUCTURED HEADINGS: Organize your briefing with clear, bold section headers for major stories.
3. CONCISE & ACTIONABLE: Avoid unnecessary filler or repetition. Every sentence must deliver high information density.
4. STRICT GROUNDING & CLICKABLE LINKS: Cite every single factual assertion using bracketed numbers corresponding to the sources. Format citations or source mentions as clickable markdown links to their article URLs, e.g. [Source Name](url) or [[1]](url).
5. NO HALLUCINATIONS: Answer ONLY from the provided source articles."""


def build_prompt(
    query: str,
    results: list[SearchResult],
) -> tuple[str, str, list[CitationSource]]:
    """Build the system prompt and user message with citation-tagged context."""
    citations: list[CitationSource] = []
    context_blocks: list[str] = []

    for i, result in enumerate(results, start=1):
        # Extract clean 2-sentence summary snippet for cards
        clean_text = result.chunk_text.strip()
        sentences = [s.strip() for s in clean_text.replace("\n", " ").split(". ") if len(s.strip()) > 15]
        card_summary = ". ".join(sentences[:2]) + ("." if sentences else "") if sentences else clean_text[:200]

        citation = CitationSource(
            index=i,
            article_id=result.article_id,
            source=result.source,
            url=result.url,
            published_at=result.published_at,
            title=result.title or f"{result.source} News Report",
            image_url=result.image_url,
            summary=card_summary,
        )
        citations.append(citation)

        header = f"[{i}] Source: {result.source}"
        if result.title:
            header += f" | Title: {result.title}"
        if result.published_at:
            header += f" | Published: {result.published_at}"
        header += f"\nURL: {result.url}"

        context_blocks.append(f"{header}\n{result.chunk_text}")

    context_section = "\n\n---\n\n".join(context_blocks)

    user_message = f"""Based on the verified source articles below, synthesize an executive, structured news briefing answering the user's question. Make sure to cite every claim with [1], [2], etc.

SOURCES:
{context_section}

QUESTION: {query}"""

    return SYSTEM_PROMPT, user_message, citations
