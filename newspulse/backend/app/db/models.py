import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    trust_tier: Mapped[int] = mapped_column(Integer, default=1)
    poll_interval_min: Mapped[int] = mapped_column(Integer, default=15)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    etag: Mapped[str | None] = mapped_column(String(512))
    last_build_date: Mapped[str | None] = mapped_column(String(512))

    articles: Mapped[list["Article"]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    full_text: Mapped[str | None] = mapped_column(Text)
    is_duplicate_of: Mapped[str | None] = mapped_column(String(36), ForeignKey("articles.id"))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    source: Mapped["Source"] = relationship(back_populates="articles")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="article")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    article_id: Mapped[str] = mapped_column(String(36), ForeignKey("articles.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(255))

    article: Mapped["Article"] = relationship(back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
