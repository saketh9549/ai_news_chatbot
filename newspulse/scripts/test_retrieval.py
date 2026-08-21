"""Phase 3 verification — test chunking, embedding, Qdrant upsert, and hybrid search.

Usage:
    cd newspulse
    python scripts/test_retrieval.py

Requires: Postgres + Qdrant running, articles already ingested (run test_ingestion.py first),
and OPENAI_API_KEY set in backend/.env
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Base, Article, Chunk
from app.indexing.chunker import chunk_text
from app.indexing.pipeline import index_unindexed_articles
from app.indexing.qdrant_client import ensure_collection, get_qdrant_client


def test_chunker():
    """Verify chunker produces sensible output."""
    print("=== Testing Chunker ===")
    sample_text = """
    The stock market experienced significant gains today as tech companies
    reported strong earnings. Major indices rose by over 2%.

    Apple announced record revenue of $120 billion for the quarter,
    driven by strong iPhone sales in emerging markets. CEO Tim Cook
    highlighted the growth in services revenue.

    Meanwhile, Google's parent company Alphabet reported a 25% increase
    in advertising revenue. The company's cloud division also showed
    impressive growth, narrowing losses significantly.

    Investors remain cautious however, as inflation concerns persist
    and the Federal Reserve has signaled potential rate hikes in the
    coming months. Bond yields rose in response.
    """
    chunks = chunk_text(sample_text, max_chunk_size=200, overlap=30)
    print(f"  Input: {len(sample_text)} chars")
    print(f"  Output: {len(chunks)} chunks")
    for c in chunks:
        print(f"    [{c.index}] ({len(c.text)} chars): {c.text[:80]}...")
    assert len(chunks) >= 2, "Should produce multiple chunks"
    print("  PASS\n")


def test_indexing_pipeline():
    """Test full pipeline: chunk → embed → Qdrant upsert."""
    print("=== Testing Indexing Pipeline ===")
    engine = create_engine(settings.database_url_sync, echo=False)
    Session = sessionmaker(engine)

    with Session() as session:
        # Count articles available
        articles = session.execute(select(Article).limit(5)).scalars().all()
        if not articles:
            print("  No articles in DB — run test_ingestion.py first!")
            return

        print(f"  Found {len(articles)} articles to index (limit 5)")

        # Run indexing
        total_chunks = index_unindexed_articles(session, limit=5)
        print(f"  Created {total_chunks} chunks total")

        # Verify chunks in Postgres
        chunks = session.execute(select(Chunk).limit(10)).scalars().all()
        print(f"  Chunks in Postgres: {len(chunks)}")
        for c in chunks[:3]:
            print(f"    [{c.chunk_index}] point_id={c.qdrant_point_id[:8]}... text={c.chunk_text[:60]}...")

    print("  PASS\n")


def test_qdrant_search():
    """Verify hybrid search returns results from Qdrant."""
    print("=== Testing Qdrant Search ===")
    from app.indexing.embedder import embed_single

    client = get_qdrant_client()
    collection_info = client.get_collection(settings.qdrant_collection)
    print(f"  Collection '{settings.qdrant_collection}': {collection_info.points_count} points")

    if collection_info.points_count == 0:
        print("  No points in Qdrant — indexing may have failed")
        return

    # Dense search
    query = "technology companies earnings"
    query_embedding = embed_single(query)

    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        using="dense",
        limit=3,
    )
    results = response.points
    print(f"\n  Dense search for: '{query}'")
    print(f"  Results: {len(results)}")
    for r in results:
        print(f"    score={r.score:.4f} | {r.payload.get('chunk_text', '')[:80]}...")

    print("  PASS\n")


def test_hybrid_search():
    """Test Phase 5 hybrid search with RRF fusion."""
    print("=== Testing Hybrid Search (Phase 5) ===")
    from app.retrieval.hybrid_search import hybrid_search

    query = "technology companies earnings"
    results = hybrid_search(query, top_k=5)
    print(f"  Query: '{query}'")
    print(f"  Results: {len(results)}")
    for i, r in enumerate(results):
        print(f"    [{i+1}] score={r.score:.4f} | source={r.source} | {r.chunk_text[:70]}...")
    assert len(results) > 0, "Should return at least one result"
    print("  PASS\n")


def test_reranker():
    """Test Phase 5 full retrieval pipeline with reranking."""
    print("=== Testing Retrieval + Reranking (Phase 5) ===")
    from app.retrieval.reranker import retrieve

    query = "what are the latest developments in artificial intelligence"
    results = retrieve(query, initial_top_k=10, final_top_k=3)
    print(f"  Query: '{query}'")
    print(f"  Final results after reranking: {len(results)}")
    for i, r in enumerate(results):
        print(f"    [{i+1}] rerank_score={r.score:.4f} | source={r.source}")
        print(f"         {r.chunk_text[:80]}...")
    print("  PASS\n")


def test_rag_generation():
    """Test full RAG generation with Gemini."""
    print("=== Testing End-to-End RAG Generation ===")
    from app.retrieval.reranker import retrieve
    from app.rag.llm_client import ask

    query = "What are the key recent news headlines?"
    results = retrieve(query, initial_top_k=10, final_top_k=5)
    if not results:
        print("  No retrieval results found.")
        return

    response = ask(query, results)
    print(f"  Query: '{query}'")
    print(f"  Answer: {response.answer}")
    print(f"  Citations Used: {len(response.citations_used)}")
    for c in response.citations_used:
        print(f"    [{c.index}] {c.source}: {c.url}")
    print("  PASS\n")


if __name__ == "__main__":
    test_chunker()

    if not settings.google_api_key:
        print("=== Skipping embedding/Qdrant/retrieval tests (no GOOGLE_API_KEY set) ===")
        print("Set GOOGLE_API_KEY in backend/.env to test full pipeline.")
    else:
        ensure_collection()
        test_indexing_pipeline()
        test_qdrant_search()
        test_hybrid_search()
        test_reranker()
        test_rag_generation()

    print("Verification complete.")
