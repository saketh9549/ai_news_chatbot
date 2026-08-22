"""Hybrid search: dense (cosine) + sparse (BM25) with Reciprocal Rank Fusion + recency boost."""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from qdrant_client.models import SparseVector

from app.config import settings
from app.indexing.embedder import embed_single
from app.indexing.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    point_id: str
    article_id: str
    chunk_text: str
    source: str
    category: str
    url: str
    published_at: str | None
    score: float
    title: str = ""
    image_url: str | None = None


def _compute_sparse_query(text: str) -> SparseVector:
    """Compute sparse vector for BM25-style search (same logic as indexing)."""
    tokens = text.lower().split()
    term_freqs: dict[int, float] = {}
    for token in tokens:
        idx = abs(hash(token)) % 100_000
        term_freqs[idx] = term_freqs.get(idx, 0) + 1.0
    indices = sorted(term_freqs.keys())
    values = [term_freqs[i] for i in indices]
    return SparseVector(indices=indices, values=values)


def _reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists using RRF. Returns (point_id, fused_score) sorted desc."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (point_id, _original_score) in enumerate(ranked):
            scores[point_id] = scores.get(point_id, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def hybrid_search(
    query: str,
    top_k: int = 30,
    category_filter: str | None = None,
) -> list[SearchResult]:
    """Execute hybrid search: dense + sparse with RRF fusion and article diversity.

    Returns up to top_k results sorted by fused relevance score.
    """
    client = get_qdrant_client()
    collection = settings.qdrant_collection

    # Dense search
    query_embedding = embed_single(query)

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    search_filter = None
    if category_filter and category_filter.lower() != "all":
        search_filter = Filter(
            must=[FieldCondition(key="category", match=MatchValue(value=category_filter.lower()))]
        )

    # Fetch larger candidate pool for fusion
    fetch_limit = max(top_k * 3, 50)

    # Parallel Dense + Sparse querying to reduce network latency
    sparse_query = _compute_sparse_query(query)
    
    dense_results = []
    sparse_results = []

    def _query_dense():
        try:
            return client.query_points(
                collection_name=collection,
                query=query_embedding,
                using="dense",
                query_filter=search_filter,
                limit=fetch_limit,
            ).points
        except Exception:
            return client.query_points(
                collection_name=collection,
                query=query_embedding,
                using="dense",
                limit=fetch_limit,
            ).points

    def _query_sparse():
        try:
            return client.query_points(
                collection_name=collection,
                query=sparse_query,
                using="bm25",
                query_filter=search_filter,
                limit=fetch_limit,
            ).points
        except Exception:
            return client.query_points(
                collection_name=collection,
                query=sparse_query,
                using="bm25",
                limit=fetch_limit,
            ).points

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_dense = executor.submit(_query_dense)
        f_sparse = executor.submit(_query_sparse)
        dense_results = f_dense.result()
        sparse_results = f_sparse.result()

    # Enforce strict category matching if category_filter is set
    if category_filter and category_filter.lower() != "all":
        target_cat = category_filter.lower()
        dense_results = [r for r in dense_results if r.payload and r.payload.get("category", "").lower() == target_cat]
        sparse_results = [r for r in sparse_results if r.payload and r.payload.get("category", "").lower() == target_cat]

    # Build ranked lists for RRF
    dense_ranked = [(str(r.id), r.score) for r in dense_results]
    sparse_ranked = [(str(r.id), r.score) for r in sparse_results]

    fused = _reciprocal_rank_fusion([dense_ranked, sparse_ranked])

    # Collect payloads from both result sets
    payload_map: dict[str, dict] = {}
    for r in dense_results:
        payload_map[str(r.id)] = r.payload
    for r in sparse_results:
        payload_map[str(r.id)] = r.payload

    # Apply recency boost: newer articles get a score multiplier
    now = datetime.now(timezone.utc)
    boosted: list[tuple[str, float]] = []
    for point_id, score in fused:
        payload = payload_map.get(point_id)
        if not payload:
            continue
        recency_multiplier = 1.0
        pub = payload.get("published_at")
        if pub:
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                age_hours = max((now - pub_dt).total_seconds() / 3600, 1)
                # Logarithmic decay: articles from last hour get ~1.4x, 24h ~1.2x, 7d ~1.0x
                recency_multiplier = 1.0 + 0.4 / math.log2(age_hours + 2)
            except (ValueError, TypeError):
                pass
        boosted.append((point_id, score * recency_multiplier))

    boosted.sort(key=lambda x: x[1], reverse=True)

    # Article diversity filter: Allow at most 2 chunks per unique article to ensure multi-story coverage
    article_counts: dict[str, int] = defaultdict(int)
    results: list[SearchResult] = []

    for point_id, score in boosted:
        payload = payload_map[point_id]
        art_id = payload.get("article_id", point_id)
        if article_counts[art_id] >= 2:
            continue

        article_counts[art_id] += 1
        results.append(SearchResult(
            point_id=point_id,
            article_id=art_id,
            chunk_text=payload.get("chunk_text", ""),
            source=payload.get("source", ""),
            category=payload.get("category", ""),
            url=payload.get("url", ""),
            published_at=payload.get("published_at"),
            score=score,
            title=payload.get("title", ""),
            image_url=payload.get("image_url"),
        ))

        if len(results) >= top_k:
            break

    # Fallback: if category filter was active but returned fewer than 3 results, relax filter
    if category_filter and len(results) < 3:
        logger.info("Category filter '%s' yielded only %d results. Broadening search...", category_filter, len(results))
        return hybrid_search(query, top_k=top_k, category_filter=None)

    logger.info(
        "Hybrid search for '%s': %d dense + %d sparse -> %d diverse results across %d articles",
        query[:50], len(dense_results), len(sparse_results), len(results), len(article_counts),
    )
    return results
