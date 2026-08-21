"""Qdrant collection setup and upsert operations for hybrid search."""

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseVector,
    VectorParams,
    SparseVectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        if settings.qdrant_api_key:
            # Qdrant Cloud — connect via URL with API key
            _client = QdrantClient(
                url=f"https://{settings.qdrant_host}",
                api_key=settings.qdrant_api_key,
                timeout=10.0,
            )
        else:
            # Local Qdrant — connect via host:port
            _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=10.0)
    return _client


def ensure_collection() -> None:
    """Create the news_chunks collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                "dense": VectorParams(size=settings.embedding_dim, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams()
            },
        )
        logger.info("Created Qdrant collection: %s", settings.qdrant_collection)
    else:
        logger.info("Qdrant collection already exists: %s", settings.qdrant_collection)

    # Ensure payload keyword indexes exist for filtering
    for field in ["category", "source", "article_id"]:
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def _compute_sparse_vector(text: str) -> SparseVector:
    """Compute a simple term-frequency sparse vector for BM25-style search."""
    tokens = text.lower().split()
    term_freqs: dict[int, float] = {}
    for token in tokens:
        # Use hash as index for sparse vector
        idx = abs(hash(token)) % 100_000
        term_freqs[idx] = term_freqs.get(idx, 0) + 1.0

    indices = sorted(term_freqs.keys())
    values = [term_freqs[i] for i in indices]
    return SparseVector(indices=indices, values=values)


def upsert_chunks(
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> list[str]:
    """Upsert chunk vectors + metadata into Qdrant.

    Each chunk dict must have: article_id, source, category, published_at, url, chunk_text, chunk_index
    Returns list of Qdrant point IDs.
    """
    client = get_qdrant_client()
    points: list[PointStruct] = []
    point_ids: list[str] = []

    for chunk, embedding in zip(chunks, embeddings):
        point_id = str(uuid.uuid4())
        point_ids.append(point_id)

        sparse = _compute_sparse_vector(chunk["chunk_text"])

        point = PointStruct(
            id=point_id,
            vector={
                "dense": embedding,
            },
            payload={
                "article_id": str(chunk["article_id"]),
                "source": chunk["source"],
                "category": chunk.get("category", ""),
                "published_at": chunk.get("published_at"),
                "url": chunk["url"],
                "chunk_text": chunk["chunk_text"],
            },
        )
        # Attach sparse vector
        point.vector["bm25"] = sparse  # type: ignore

        points.append(point)

    if points:
        client.upsert(collection_name=settings.qdrant_collection, points=points)
        logger.info("Upserted %d points to Qdrant", len(points))

    return point_ids
