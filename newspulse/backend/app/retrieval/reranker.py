"""Cross-encoder reranking and optimized retrieval pipeline."""

import logging

from app.config import settings
from app.retrieval.hybrid_search import SearchResult

logger = logging.getLogger(__name__)

_model = None


def _get_reranker():
    """Lazy-load the cross-encoder model."""
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading reranker model: %s", settings.reranker_model)
        _model = CrossEncoder(settings.reranker_model)
    return _model


def rerank(
    query: str,
    results: list[SearchResult],
    top_k: int = 10,
) -> list[SearchResult]:
    """Rerank search results using a cross-encoder model."""
    if not results:
        return []

    if len(results) <= top_k:
        return results

    model = _get_reranker()

    # Create query-document pairs for the cross-encoder
    pairs = [(query, r.chunk_text) for r in results]
    scores = model.predict(pairs)

    # Attach reranker scores and sort
    scored = list(zip(results, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    reranked = []
    for result, score in scored[:top_k]:
        result.score = float(score)
        reranked.append(result)

    logger.info(
        "Reranked %d results down to top %d (scores: %.4f to %.4f)",
        len(results), len(reranked),
        reranked[0].score if reranked else 0,
        reranked[-1].score if reranked else 0,
    )
    return reranked


def retrieve(
    query: str,
    initial_top_k: int = 20,
    final_top_k: int = 10,
    category_filter: str | None = None,
) -> list[SearchResult]:
    """Full retrieval pipeline: hybrid search -> optional rerank -> top-k.

    Uses high-speed dense (3072d) + sparse (BM25) RRF search with recency boosting.
    """
    from app.retrieval.hybrid_search import hybrid_search

    candidates = hybrid_search(query, top_k=initial_top_k, category_filter=category_filter)

    # Dynamic Live NewsAPI Fallback: If local database has insufficient results (< 4), fetch live web news
    if len(candidates) < 4 and settings.newsapi_key:
        try:
            from app.ingestion.newsapi_client import fetch_and_index_live_news
            logger.info("Local candidates low (%d), triggering live NewsAPI search for '%s'", len(candidates), query[:40])
            indexed_count = fetch_and_index_live_news(query, category=category_filter, limit=8)
            if indexed_count > 0:
                candidates = hybrid_search(query, top_k=initial_top_k, category_filter=category_filter)
        except Exception as e:
            logger.warning("Live NewsAPI fallback failed (%s), proceeding with existing candidates", e)

    if not candidates:
        logger.warning("No results found for query: '%s'", query[:50])
        return []

    # If CPU cross-encoder reranking is disabled, use fast hybrid RRF results directly (< 500ms)
    if not getattr(settings, "enable_reranker", False):
        return candidates[:final_top_k]

    try:
        # Limit cross-encoder candidates pool to max 14 to avoid high CPU inference latency
        rerank_pool = candidates[:max(final_top_k + 4, 14)]
        return rerank(query, rerank_pool, top_k=final_top_k)
    except Exception:
        logger.exception("Reranker failed, returning hybrid search results directly")
        return candidates[:final_top_k]
