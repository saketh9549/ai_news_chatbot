"""Indexing pipeline: chunk articles → embed → upsert to Qdrant + store chunk records."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article, Chunk, Source
from app.indexing.chunker import chunk_text
from app.indexing.embedder import embed_texts
from app.indexing.qdrant_client import ensure_collection, upsert_chunks, get_qdrant_client
from app.ingestion.dedup import check_semantic_duplicate
from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 32


def index_article(article: Article, source: Source, session: Session) -> int:
    """Chunk, embed, and index a single article. Returns number of chunks created."""
    if not article.full_text:
        logger.warning("Article %s has no text, skipping", article.id)
        return 0

    # Check if already indexed
    existing_chunks = session.execute(
        select(Chunk).where(Chunk.article_id == article.id)
    ).scalars().all()
    if existing_chunks:
        logger.debug("Article %s already indexed (%d chunks)", article.id, len(existing_chunks))
        return 0

    # Chunk the article text
    text_chunks = chunk_text(article.full_text)
    if not text_chunks:
        return 0

    # Embed all chunks (single API call for the batch)
    chunk_texts = [c.text for c in text_chunks]
    embeddings = embed_texts(chunk_texts)

    # Tier 2 semantic dedup: use the first chunk's embedding (already computed)
    # to check Qdrant for near-duplicate content within a time window
    qdrant = get_qdrant_client()
    dup_article_id = check_semantic_duplicate(
        embedding=embeddings[0],
        article_url=article.url,
        published_at=article.published_at,
        qdrant_client=qdrant,
        collection_name=settings.qdrant_collection,
    )
    if dup_article_id:
        article.is_duplicate_of = dup_article_id
        session.commit()
        logger.info(
            "Article '%s' is semantic duplicate of %s — skipping indexing",
            article.title[:60],
            dup_article_id,
        )
        return 0

    # Prepare metadata for Qdrant
    chunk_metadata = [
        {
            "article_id": article.id,
            "title": article.title,
            "image_url": article.image_url,
            "source": source.name,
            "category": source.category or "",
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "url": article.url,
            "chunk_text": c.text,
            "chunk_index": c.index,
        }
        for c in text_chunks
    ]

    # Upsert to Qdrant
    point_ids = upsert_chunks(chunk_metadata, embeddings)

    # Store chunk records in Postgres
    for tc, point_id in zip(text_chunks, point_ids):
        chunk = Chunk(
            article_id=article.id,
            chunk_index=tc.index,
            chunk_text=tc.text,
            qdrant_point_id=point_id,
        )
        session.add(chunk)

    session.commit()
    logger.info("Indexed article '%s': %d chunks", article.title[:60], len(text_chunks))
    return len(text_chunks)


def index_unindexed_articles(session: Session, limit: int = 100) -> int:
    """Find articles without chunks and index them. Returns total chunks created."""
    ensure_collection()

    # Articles that have no chunks yet
    articles_with_chunks = select(Chunk.article_id).distinct()
    unindexed = session.execute(
        select(Article)
        .where(Article.id.notin_(articles_with_chunks))
        .where(Article.full_text.isnot(None))
        .limit(limit)
    ).scalars().all()

    if not unindexed:
        logger.info("No unindexed articles found")
        return 0

    logger.info("Indexing %d articles", len(unindexed))
    total_chunks = 0

    for article in unindexed:
        source = session.execute(
            select(Source).where(Source.id == article.source_id)
        ).scalar_one()
        try:
            total_chunks += index_article(article, source, session)
        except Exception:
            logger.exception("Error indexing article %s", article.id)

    return total_chunks
