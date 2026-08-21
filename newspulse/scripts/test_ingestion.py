"""Manual test script for Phase 1 — verifies RSS ingestion works end-to-end.

Usage:
    cd newspulse/backend
    python -m scripts.test_ingestion

Requires: Postgres running (via docker-compose), migrations applied.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Base, Source, Article
from app.ingestion.collector import poll_all_feeds

SAMPLE_FEEDS = [
    {"name": "BBC News", "feed_url": "http://feeds.bbci.co.uk/news/rss.xml", "category": "general"},
    {"name": "TechCrunch", "feed_url": "https://techcrunch.com/feed/", "category": "technology"},
    {"name": "Reuters World", "feed_url": "https://www.reutersagency.com/feed/", "category": "world"},
]


def main():
    engine = create_engine(settings.database_url_sync, echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)

    with Session() as session:
        # Seed sources if empty
        existing = session.execute(select(Source)).scalars().all()
        if not existing:
            print("\n--- Seeding sample RSS sources ---")
            for feed in SAMPLE_FEEDS:
                source = Source(**feed)
                session.add(source)
            session.commit()
            print(f"Added {len(SAMPLE_FEEDS)} sources.\n")

        # Poll all feeds
        print("\n--- Polling all feeds ---")
        total_new = poll_all_feeds(session)
        print(f"\nTotal new articles ingested: {total_new}")

        # Report what's in the database
        articles = session.execute(select(Article).order_by(Article.ingested_at.desc()).limit(10)).scalars().all()
        print(f"\n--- Latest articles in DB (up to 10) ---")
        for a in articles:
            print(f"  [{a.source_id}] {a.title[:80]}")
            print(f"       URL: {a.url}")
            print(f"       Published: {a.published_at}")
            print()

        total_articles = session.execute(select(Article)).scalars().all()
        print(f"Total articles in database: {len(total_articles)}")


if __name__ == "__main__":
    main()
