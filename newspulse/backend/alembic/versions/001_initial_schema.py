"""Initial schema — sources, articles, chunks, chat

Revision ID: 001
Revises: None
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("feed_url", sa.String(2048), unique=True, nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("trust_tier", sa.Integer, server_default="1"),
        sa.Column("poll_interval_min", sa.Integer, server_default="15"),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("etag", sa.String(512)),
        sa.Column("last_build_date", sa.String(512)),
    )

    op.create_table(
        "articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("url", sa.String(2048), unique=True, nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("full_text", sa.Text),
        sa.Column("is_duplicate_of", UUID(as_uuid=True), sa.ForeignKey("articles.id")),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("article_id", UUID(as_uuid=True), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("qdrant_point_id", sa.String(255)),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations_json", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("chunks")
    op.drop_table("articles")
    op.drop_table("sources")
