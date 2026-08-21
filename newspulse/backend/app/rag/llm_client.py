"""LLM client for RAG answers — uses Google Gemini API with instant fallback and zero-delay retry."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Generator

from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

from app.config import settings
from app.rag.prompt_builder import CitationSource
from app.retrieval.hybrid_search import SearchResult

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from google.genai.types import HttpOptions
        _client = genai.Client(
            api_key=settings.google_api_key,
            http_options=HttpOptions(timeout=15000),
        )
        if hasattr(_client, "_api_client") and hasattr(_client._api_client, "_retry"):
            _client._api_client._retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return _client


def _get_candidate_models() -> list[str]:
    """Return fast model candidates."""
    models = [
        settings.llm_model,
        "models/gemini-3.5-flash-lite",
        "models/gemini-flash-lite-latest",
        "models/gemini-flash-latest",
    ]
    seen = set()
    ordered = []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


@dataclass
class RAGResponse:
    answer: str
    citations_used: list[CitationSource]
    raw_response: str


def synthesize_extractive_briefing(query: str, results: list[SearchResult]) -> tuple[str, list[CitationSource]]:
    """Synthesize a structured intelligence briefing with crisp summaries from top retrieved sources."""
    citations: list[CitationSource] = []
    lines = [
        f"### **Executive Intelligence Briefing: {query}**\n",
        f"Here is a summary of the latest verified developments from **{len(results[:6])} global sources**:\n",
    ]

    for i, r in enumerate(results[:6], 1):
        source_name = r.source or "News Wire"
        pub_date = f" ({r.published_at[:10]})" if r.published_at else ""

        # Clean text and extract key summary sentences (not the whole raw article)
        clean_text = r.chunk_text.strip().replace("\r", " ")
        sentences = [
            s.strip() for s in clean_text.replace("\n", " ").split(". ")
            if len(s.strip()) > 20 and not any(j in s.lower() for j in ["cookie", "subscribe", "sign up", "terms of", "privacy policy", "jump to", "share this"])
        ]
        summary_sentences = sentences[:2]
        clean_summary = ". ".join(summary_sentences) + ("." if summary_sentences and not summary_sentences[-1].endswith(".") else "") if summary_sentences else clean_text[:250] + "..."

        citation = CitationSource(
            index=i,
            article_id=r.article_id,
            source=source_name,
            url=r.url,
            published_at=r.published_at,
            title=r.title or f"{source_name} Report",
            image_url=r.image_url,
            summary=clean_summary,
        )
        citations.append(citation)

        headline = r.title if r.title else f"{source_name} Update"
        lines.append(f"• **[{headline}]({r.url})** — *[{source_name}]({r.url}){pub_date}*")
        lines.append(f"  {clean_summary} [**[[{i}]]({r.url})**]\n")

    return "\n".join(lines), citations


def generate_answer(
    system_prompt: str,
    user_message: str,
    citations: list[CitationSource],
    max_tokens: int = 2048,
    raw_results: list[SearchResult] | None = None,
) -> RAGResponse:
    """Call Gemini to generate a citation-grounded answer with zero-delay fallback."""
    client = _get_client()
    candidate_models = _get_candidate_models()

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"{system_prompt}\n\n{user_message}",
                config=GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                ),
            )
            answer_text = response.text or ""
            if not answer_text.strip():
                continue

            used_indices = set(int(m) for m in re.findall(r"\[(\d+)\]", answer_text))
            citations_used = [c for c in citations if c.index in used_indices]

            logger.info(
                "LLM response using model '%s': %d chars, %d citations used",
                model_name, len(answer_text), len(citations_used),
            )

            return RAGResponse(
                answer=answer_text,
                citations_used=citations_used,
                raw_response=answer_text,
            )
        except Exception as e:
            logger.warning("Model '%s' failed (%s), attempting next fallback...", model_name, e)

    # If all API models are rate limited or unavailable, return the extractive synthesis
    if raw_results:
        briefing, ext_citations = synthesize_extractive_briefing("News Briefing", raw_results)
        return RAGResponse(answer=briefing, citations_used=ext_citations, raw_response=briefing)

    raise RuntimeError("All LLM models failed to generate content.")


def ask(
    query: str,
    results: list[SearchResult],
    max_tokens: int = 2048,
) -> RAGResponse:
    """End-to-end RAG: build prompt from retrieval results, call LLM, parse citations."""
    from app.rag.prompt_builder import build_prompt

    system_prompt, user_message, citations = build_prompt(query, results)
    return generate_answer(system_prompt, user_message, citations, max_tokens, raw_results=results)
