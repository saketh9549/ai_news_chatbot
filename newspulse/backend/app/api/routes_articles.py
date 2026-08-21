"""Articles endpoints: retrieve article details by ID and recent articles."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article, Source
from app.db.session import get_sync_session

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleOut(BaseModel):
    id: str
    source_name: str
    url: str
    title: str
    image_url: str | None = None
    published_at: datetime | None
    full_text: str | None
    ingested_at: datetime


class RecentArticleOut(BaseModel):
    id: str
    source_name: str
    source_category: str | None
    url: str
    title: str
    image_url: str | None = None
    published_at: datetime | None


@router.get("/recent", response_model=list[RecentArticleOut])
def get_recent_articles(
    limit: int = Query(15, ge=1, le=50),
    category: str | None = None,
    session: Session = Depends(get_sync_session),
):
    """Retrieve recent unique articles for headline ticker / discovery."""
    query = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.is_duplicate_of.is_(None))
        .order_by(Article.ingested_at.desc())
    )
    if category and category.lower() != "all":
        query = query.where(Source.category == category.lower())

    results = session.execute(query.limit(limit)).all()
    return [
        RecentArticleOut(
            id=str(article.id),
            source_name=source.name,
            source_category=source.category,
            url=article.url,
            title=article.title,
            image_url=article.image_url,
            published_at=article.published_at or article.ingested_at,
        )
        for article, source in results
    ]


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: str, session: Session = Depends(get_sync_session)):
    article = session.execute(
        select(Article).where(Article.id == article_id)
    ).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    source = session.execute(
        select(Source).where(Source.id == article.source_id)
    ).scalar_one()

    return ArticleOut(
        id=str(article.id),
        source_name=source.name,
        url=article.url,
        title=article.title,
        image_url=article.image_url,
        published_at=article.published_at,
        full_text=article.full_text,
        ingested_at=article.ingested_at,
    )
