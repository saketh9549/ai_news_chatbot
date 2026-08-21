"""Sources endpoints: CRUD for RSS feed sources."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Source
from app.db.session import get_sync_session

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    feed_url: str
    category: str | None = None
    trust_tier: int = 1
    poll_interval_min: int = 15


class SourceOut(BaseModel):
    id: str
    name: str
    feed_url: str
    category: str | None
    trust_tier: int
    poll_interval_min: int
    last_polled_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_sync_session)):
    sources = session.execute(select(Source)).scalars().all()
    return [SourceOut(id=str(s.id), name=s.name, feed_url=s.feed_url,
                      category=s.category, trust_tier=s.trust_tier,
                      poll_interval_min=s.poll_interval_min,
                      last_polled_at=s.last_polled_at) for s in sources]


@router.post("", response_model=SourceOut, status_code=201)
def create_source(data: SourceCreate, session: Session = Depends(get_sync_session)):
    existing = session.execute(
        select(Source).where(Source.feed_url == data.feed_url)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Feed URL already exists")

    source = Source(**data.model_dump())
    session.add(source)
    session.commit()
    session.refresh(source)

    return SourceOut(id=str(source.id), name=source.name, feed_url=source.feed_url,
                     category=source.category, trust_tier=source.trust_tier,
                     poll_interval_min=source.poll_interval_min,
                     last_polled_at=source.last_polled_at)


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: str, session: Session = Depends(get_sync_session)):
    source = session.execute(
        select(Source).where(Source.id == source_id)
    ).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    session.delete(source)
    session.commit()
