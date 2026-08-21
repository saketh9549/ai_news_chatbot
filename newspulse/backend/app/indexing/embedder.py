"""Embedding generation via Google GenAI (text-embedding-004)."""

import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts. Returns list of float vectors."""
    if not texts:
        return []

    client = _get_client()
    results = []
    for text in texts:
        response = client.models.embed_content(
            model=settings.embedding_model,
            contents=text,
        )
        results.append(response.embeddings[0].values)
    return results


def embed_query(text: str) -> list[float]:
    """Embed a query string."""
    client = _get_client()
    response = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
    )
    return response.embeddings[0].values


def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    return embed_query(text)
