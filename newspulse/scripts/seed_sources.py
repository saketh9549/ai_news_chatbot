"""Seed initial RSS feed sources into the database."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Base, Source

FEEDS = [
    {"name": "BBC World", "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "world"},
    {"name": "BBC Technology", "feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "technology"},
    {"name": "The Guardian World", "feed_url": "https://www.theguardian.com/world/rss", "category": "world"},
    {"name": "The Guardian Technology", "feed_url": "https://www.theguardian.com/technology/rss", "category": "technology"},
    {"name": "The Guardian Business", "feed_url": "https://www.theguardian.com/business/rss", "category": "business"},
    {"name": "NYT Homepage", "feed_url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "category": "world"},
    {"name": "NPR News", "feed_url": "https://feeds.npr.org/1001/rss.xml", "category": "world"},
    {"name": "CNN Latest", "feed_url": "https://rss.cnn.com/rss/cnn_latest.rss", "category": "world"},
    {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index", "category": "technology"},
    {"name": "Ars Technica Technology", "feed_url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category": "technology"},
    {"name": "The Verge", "feed_url": "https://www.theverge.com/rss/index.xml", "category": "technology"},
    {"name": "TechCrunch", "feed_url": "https://feeds.feedburner.com/TechCrunch", "category": "technology"},
    {"name": "MIT Technology Review", "feed_url": "https://www.technologyreview.com/feed/", "category": "technology"},
    {"name": "ScienceDaily All News", "feed_url": "https://www.sciencedaily.com/rss/all.xml", "category": "science"},
    {"name": "ScienceDaily Technology", "feed_url": "https://www.sciencedaily.com/rss/top/technology.xml", "category": "technology"},
    {"name": "ScienceDaily Health", "feed_url": "https://www.sciencedaily.com/rss/top/health.xml", "category": "science"},
    {"name": "Hacker News", "feed_url": "https://hnrss.org/frontpage", "category": "technology"},
    {"name": "arXiv AI", "feed_url": "https://rss.arxiv.org/rss/cs.AI", "category": "science"},
    {"name": "OpenAI Blog", "feed_url": "https://openai.com/blog/rss.xml", "category": "technology"},
    {"name": "NASA JPL News", "feed_url": "https://www.jpl.nasa.gov/feeds/news/", "category": "science"},
]


def main():
    engine = create_engine(settings.database_url_sync, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)

    with Session() as session:
        added_count = 0
        exists_count = 0
        for feed in FEEDS:
            exists = session.execute(
                select(Source).where(Source.feed_url == feed["feed_url"])
            ).scalar_one_or_none()
            if not exists:
                session.add(Source(**feed))
                print(f"  [+] Added: {feed['name']} ({feed['category']})")
                added_count += 1
            else:
                # Update category if needed
                exists.name = feed["name"]
                exists.category = feed["category"]
                print(f"  [=] Exists/Updated: {feed['name']}")
                exists_count += 1
        session.commit()
    print(f"\nDone. {added_count} added, {exists_count} existing/updated. Total 20 sources configured.")


if __name__ == "__main__":
    main()
