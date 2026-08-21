"""RSS feed collector — polls feeds via feedparser, respects ETag/Last-Modified."""

import logging
import re
import socket
from datetime import datetime, timezone, timedelta

import feedparser

socket.setdefaulttimeout(30)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article, Source
from app.ingestion.dedup import normalize_url, simhash, hamming_distance
from app.ingestion.extractor import extract_article_content

logger = logging.getLogger(__name__)


def poll_feed(source: Source, session: Session) -> int:
    """Poll a single RSS feed and store new articles. Returns count of new articles."""
    logger.info("Polling feed: %s (%s)", source.name, source.feed_url)

    kwargs: dict = {}
    if source.etag:
        kwargs["etag"] = source.etag
    if source.last_build_date:
        kwargs["modified"] = source.last_build_date

    feed = feedparser.parse(source.feed_url, **kwargs)

    status = getattr(feed, "status", None)
    if status == 304:
        logger.info("Feed %s not modified (304)", source.name)
        source.last_polled_at = datetime.now(timezone.utc)
        session.commit()
        return 0

    new_etag = getattr(feed, "etag", None)
    new_modified = getattr(feed, "modified", None)
    if new_etag:
        source.etag = new_etag
    if new_modified:
        source.last_build_date = new_modified

    new_count = 0
    skipped_dedup = 0
    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue

        # Tier 1a: URL normalization dedup
        canonical_url = normalize_url(link)
        existing = session.execute(select(Article).where(Article.url == canonical_url)).scalar_one_or_none()
        if existing:
            continue

        title = entry.get("title", "Untitled")

        # Tier 1b: Title SimHash dedup — check recent articles (last 48h) for near-duplicate titles
        title_hash = simhash(title)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        recent_articles = session.execute(
            select(Article).where(Article.ingested_at >= cutoff)
        ).scalars().all()

        is_dup = False
        dup_of = None
        for recent in recent_articles:
            recent_hash = simhash(recent.title)
            if hamming_distance(title_hash, recent_hash) <= 10:
                is_dup = True
                dup_of = recent.id
                break

        if is_dup:
            skipped_dedup += 1
            logger.debug("Skipped near-duplicate: '%s' (dup of %s)", title, dup_of)
            continue

        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        rss_text = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
        # If RSS summary is short, attempt web extraction
        full_text = rss_text
        if len(rss_text.strip()) < 300:
            extracted_text = extract_article_content(canonical_url)
            if extracted_text and len(extracted_text) > len(rss_text):
                full_text = extracted_text

        # Extract image from RSS entry
        image_url = None
        media_content = entry.get("media_content", [])
        if media_content and isinstance(media_content, list) and len(media_content) > 0:
            image_url = media_content[0].get("url")
        if not image_url:
            media_thumb = entry.get("media_thumbnail", [])
            if media_thumb and isinstance(media_thumb, list) and len(media_thumb) > 0:
                image_url = media_thumb[0].get("url")
        if not image_url and entry.get("enclosures"):
            for enc in entry.get("enclosures", []):
                if enc.get("type", "").startswith("image/"):
                    image_url = enc.get("href") or enc.get("url")
                    break
        if not image_url and rss_text:
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', rss_text)
            if img_match:
                image_url = img_match.group(1)

        article = Article(
            source_id=source.id,
            url=canonical_url,
            title=title,
            image_url=image_url,
            published_at=published,
            full_text=full_text,
        )
        session.add(article)
        new_count += 1

    if skipped_dedup:
        logger.info("Feed %s: %d near-duplicates skipped", source.name, skipped_dedup)

    source.last_polled_at = datetime.now(timezone.utc)
    session.commit()
    logger.info("Feed %s: %d new articles ingested", source.name, new_count)
    return new_count


def poll_all_feeds(session: Session) -> int:
    """Poll all sources and return total new articles."""
    sources = session.execute(select(Source)).scalars().all()
    total = 0
    for source in sources:
        try:
            total += poll_feed(source, session)
        except Exception:
            logger.exception("Error polling feed %s", source.name)
    return total
