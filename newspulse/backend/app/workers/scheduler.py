"""Background periodic scheduler for automated RSS ingestion."""

import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.db.session import get_sync_session_factory
from app.ingestion.collector import poll_all_feeds
from app.indexing.pipeline import index_unindexed_articles

logger = logging.getLogger(__name__)

_background_task: asyncio.Task | None = None
_running: bool = False


async def _ingestion_worker():
    """Periodic worker loop that polls and indexes articles."""
    logger.info("Starting NewsPulse background ingestion worker (interval: %d min)", settings.default_poll_interval_min)
    
    # Run an initial poll immediately upon startup
    await asyncio.sleep(5)
    
    while _running:
        try:
            logger.info("Background ingestion cycle starting...")
            session_factory = get_sync_session_factory()
            
            # Run in a threadpool to avoid blocking the async event loop with sync DB/HTTP operations
            def _run_cycle():
                with session_factory() as session:
                    # 1. RSS Feed polling
                    new_articles = poll_all_feeds(session)
                    
                    # 2. NewsAPI Global Headlines polling across categories
                    if settings.newsapi_key:
                        try:
                            from app.ingestion.newsapi_client import fetch_top_headlines, ingest_newsapi_articles
                            for cat in ["technology", "business", "science", "general"]:
                                raw = fetch_top_headlines(category=cat, limit=15)
                                if raw:
                                    ingest_newsapi_articles(session, raw, default_category=cat)
                        except Exception as ne:
                            logger.warning("NewsAPI scheduler polling error: %s", ne)

                    # 3. Index any unindexed articles
                    new_chunks = index_unindexed_articles(session)
                    return new_articles, new_chunks

            new_articles, new_chunks = await asyncio.to_thread(_run_cycle)
            logger.info("Background ingestion completed: %d new articles, %d chunks indexed", new_articles, new_chunks)
        except Exception:
            logger.exception("Error during background ingestion cycle")

        # Sleep for configured interval
        interval_seconds = max(settings.default_poll_interval_min * 60, 60)
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break

    logger.info("Background ingestion worker stopped")


def start_scheduler():
    """Start the background ingestion scheduler."""
    global _background_task, _running
    if not _running:
        _running = True
        _background_task = asyncio.create_task(_ingestion_worker())
        logger.info("Background scheduler task initiated")


def stop_scheduler():
    """Stop the background ingestion scheduler."""
    global _background_task, _running
    _running = False
    if _background_task and not _background_task.done():
        _background_task.cancel()
        logger.info("Background scheduler task cancelled")
