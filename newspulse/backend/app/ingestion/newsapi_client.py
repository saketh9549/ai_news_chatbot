"""NewsAPI.org integration for live search and category headline ingestion."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Article, Source
from app.db.session import get_sync_session_factory
from app.ingestion.dedup import normalize_url, simhash, hamming_distance
from app.ingestion.extractor import extract_article_content
from app.indexing.pipeline import index_article

logger = logging.getLogger(__name__)

BASE_URL = "https://newsapi.org/v2"


def _get_headers() -> dict[str, str]:
    return {
        "X-Api-Key": settings.newsapi_key,
        "User-Agent": "NewsPulse/0.1.0 (News Intelligence Engine)",
    }


def _get_or_create_source(session: Session, name: str, category: str) -> Source:
    clean_name = name.strip() or "NewsAPI Global"
    feed_url = f"https://newsapi.org/sources/{clean_name.lower().replace(' ', '-')}"
    source = session.execute(
        select(Source).where(Source.feed_url == feed_url)
    ).scalar_one_or_none()

    if not source:
        source = Source(
            name=clean_name,
            feed_url=feed_url,
            category=category,
            trust_tier=1,
            poll_interval_min=15,
        )
        session.add(source)
        session.commit()
        session.refresh(source)
    return source


def fetch_top_headlines(
    category: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch top headlines from NewsAPI.org."""
    if not settings.newsapi_key:
        logger.warning("NEWSAPI_KEY is not configured")
        return []

    params: dict[str, Any] = {
        "language": "en",
        "pageSize": min(limit, 50),
    }
    if category and category.lower() != "all":
        cat_map = {
            "tech": "technology",
            "technology": "technology",
            "business": "business",
            "markets": "business",
            "science": "science",
            "health": "health",
            "world": "general",
            "general": "general",
        }
        mapped_cat = cat_map.get(category.lower(), "general")
        params["category"] = mapped_cat

    if query:
        params["q"] = query

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(f"{BASE_URL}/top-headlines", params=params, headers=_get_headers())
            if resp.status_code != 200:
                logger.warning("NewsAPI top-headlines returned %d: %s", resp.status_code, resp.text[:150])
                return []
            data = resp.json()
            return data.get("articles", [])
    except Exception as e:
        logger.error("Failed to fetch top-headlines from NewsAPI: %s", e)
        return []


def search_live_news(
    query: str,
    limit: int = 10,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Search global news articles across NewsAPI.org for a specific query."""
    if not settings.newsapi_key:
        logger.warning("NEWSAPI_KEY is not configured")
        return []

    clean_q = " ".join([w for w in query.split() if len(w) > 2])[:80]
    if not clean_q:
        clean_q = query[:50]

    params: dict[str, Any] = {
        "q": clean_q,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": min(limit, 20),
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(f"{BASE_URL}/everything", params=params, headers=_get_headers())
            if resp.status_code != 200:
                logger.warning("NewsAPI everything search returned %d: %s", resp.status_code, resp.text[:150])
                return []
            data = resp.json()
            return data.get("articles", [])
    except Exception as e:
        logger.error("Failed to search live news from NewsAPI: %s", e)
        return []


def ingest_newsapi_articles(
    session: Session,
    raw_articles: list[dict[str, Any]],
    default_category: str = "general",
) -> list[tuple[Article, Source]]:
    """Process, deduplicate, and persist NewsAPI raw articles to the database."""
    saved: list[tuple[Article, Source]] = []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    recent_articles = session.execute(
        select(Article).where(Article.ingested_at >= cutoff)
    ).scalars().all()

    for item in raw_articles:
        raw_title = (item.get("title") or "").strip()
        raw_url = (item.get("url") or "").strip()

        if not raw_title or not raw_url or raw_title == "[Removed]" or "removed.com" in raw_url:
            continue

        canonical_url = normalize_url(raw_url)
        existing = session.execute(select(Article).where(Article.url == canonical_url)).scalar_one_or_none()
        if existing:
            continue

        # SimHash title dedup
        title_hash = simhash(raw_title)
        is_dup = False
        for recent in recent_articles:
            recent_hash = simhash(recent.title)
            if hamming_distance(title_hash, recent_hash) <= 10:
                is_dup = True
                break

        if is_dup:
            continue

        source_name = (item.get("source", {}).get("name") or "NewsAPI Global").strip()
        source = _get_or_create_source(session, source_name, default_category)

        description = item.get("description") or ""
        content = item.get("content") or ""

        text_body = f"{description}\n\n{content}".strip() or raw_title

        pub_date = None
        pub_str = item.get("publishedAt")
        if pub_str:
            try:
                pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pub_date = datetime.now(timezone.utc)
        else:
            pub_date = datetime.now(timezone.utc)

        img_url = item.get("urlToImage") or None

        article = Article(
            source_id=source.id,
            url=canonical_url,
            title=raw_title,
            image_url=img_url,
            published_at=pub_date,
            full_text=text_body,
        )
        session.add(article)
        saved.append((article, source))

    if saved:
        session.commit()
        for art, _ in saved:
            session.refresh(art)
        logger.info("Ingested %d fresh articles from NewsAPI", len(saved))

    return saved


def fetch_and_index_live_news(
    query: str,
    category: str | None = None,
    limit: int = 8,
) -> int:
    """Live search fallback: fetch articles for query from NewsAPI, save, and index to Qdrant."""
    raw = search_live_news(query, limit=limit, category=category)
    if not raw:
        return 0

    factory = get_sync_session_factory()
    with factory() as session:
        article_pairs = ingest_newsapi_articles(session, raw, default_category=category or "general")
        indexed_chunks = 0
        for article, source in article_pairs:
            try:
                chunks_count = index_article(article, source, session)
                indexed_chunks += chunks_count
            except Exception as e:
                logger.error("Failed to index live article '%s': %s", article.title[:40], e)
        return indexed_chunks
