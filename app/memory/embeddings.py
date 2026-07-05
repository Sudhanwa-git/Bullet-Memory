"""
Embedding Generator — wraps the configured embedding provider.

Responsible for generating vector representations for memory content.
Embedding generation happens AFTER importance scoring to avoid wasting API calls.
"""

from __future__ import annotations

import time

import structlog

from app.adapters.embedding import EmbeddingAdapter

logger = structlog.get_logger(__name__)


class EmbeddingGenerator:
    """
    Thin wrapper around the embedding adapter.

    Isolates the rest of the application from provider-specific details.
    """

    def __init__(self, adapter: EmbeddingAdapter) -> None:
        self._adapter = adapter

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text string."""
        t0 = time.perf_counter()
        vector = await self._adapter.embed(text)
        logger.debug(
            "embeddings.embed.done",
            dims=len(vector),
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in one call."""
        t0 = time.perf_counter()
        vectors = await self._adapter.embed_batch(texts)
        logger.info(
            "embeddings.embed_batch.done",
            count=len(vectors),
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return vectors
