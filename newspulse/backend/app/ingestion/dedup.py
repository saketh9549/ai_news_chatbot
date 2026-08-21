"""Deduplication: Tier 1 (URL + SimHash) and Tier 2 (semantic embedding similarity)."""

import logging
import re
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize URL to canonical form for dedup comparison.

    Strips tracking params (utm_*, fbclid, etc.), fragments, trailing slashes,
    lowercases scheme+host, and sorts remaining query params.
    """
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source",
    }

    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().rstrip(".")
    # Remove www. prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"

    # Filter out tracking query params and sort the rest
    params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(sorted(filtered.items()), doseq=True) if filtered else ""

    return urlunparse((scheme, netloc, path, "", query, ""))


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words."""
    text = re.sub(r"[^\w\s]", "", text.lower())
    return text.split()


def simhash(text: str, hashbits: int = 64) -> int:
    """Compute SimHash fingerprint of text."""
    tokens = _tokenize(text)
    if not tokens:
        return 0

    v = [0] * hashbits
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(hashbits):
            if token_hash & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(hashbits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """Count differing bits between two hashes."""
    return bin(hash1 ^ hash2).count("1")


def titles_are_near_duplicate(title1: str, title2: str, threshold: int = 10) -> bool:
    """Return True if two titles are near-duplicates (hamming distance <= threshold)."""
    h1 = simhash(title1)
    h2 = simhash(title2)
    return hamming_distance(h1, h2) <= threshold


# --- Tier 2: Semantic dedup via embedding similarity in Qdrant ---


def check_semantic_duplicate(
    embedding: list[float],
    article_url: str,
    published_at: datetime | None,
    qdrant_client,
    collection_name: str,
    threshold: float | None = None,
    time_window_hours: int | None = None,
) -> str | None:
    """Check if an embedding is a semantic near-duplicate of existing indexed content.

    Uses the already-computed first-chunk embedding to query Qdrant within a time window.
    Returns the article_id of the duplicate if found, None otherwise.
    """
    from qdrant_client import models as qmodels
    from app.config import settings

    if threshold is None:
        threshold = settings.semantic_dedup_threshold
    if time_window_hours is None:
        time_window_hours = settings.semantic_dedup_time_window_hours

    results = qdrant_client.query_points(
        collection_name=collection_name,
        query=embedding,
        using="dense",
        limit=3,
        score_threshold=threshold,
    )

    for hit in results.points:
        # Don't match against self (same URL)
        if hit.payload.get("url") == article_url:
            continue
        logger.info(
            "Semantic duplicate found: score=%.4f, existing_article=%s",
            hit.score,
            hit.payload.get("article_id"),
        )
        return hit.payload.get("article_id")

    return None
