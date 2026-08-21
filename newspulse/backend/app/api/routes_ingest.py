"""Ingestion endpoints: trigger feed polling and indexing."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.ingestion.collector import poll_all_feeds
from app.indexing.pipeline import index_unindexed_articles

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestResult(BaseModel):
    new_articles: int
    new_chunks: int


@router.post("/run", response_model=IngestResult)
def run_ingestion(session: Session = Depends(get_sync_session)):
    """Trigger a full ingestion cycle: poll feeds + index new articles."""
    new_articles = poll_all_feeds(session)
    new_chunks = index_unindexed_articles(session)
    return IngestResult(new_articles=new_articles, new_chunks=new_chunks)


class PollResult(BaseModel):
    new_articles: int


@router.post("/poll", response_model=PollResult)
def poll_feeds(session: Session = Depends(get_sync_session)):
    """Poll RSS feeds only (no indexing)."""
    new_articles = poll_all_feeds(session)
    return PollResult(new_articles=new_articles)


class IndexResult(BaseModel):
    new_chunks: int


@router.post("/index", response_model=IndexResult)
def index_articles(limit: int = 100, session: Session = Depends(get_sync_session)):
    """Index unindexed articles into Qdrant."""
    new_chunks = index_unindexed_articles(session, limit=limit)
    return IndexResult(new_chunks=new_chunks)
