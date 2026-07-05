"""
Memory Retriever — semantic search over the vector store.

Retrieval is intentionally separate from storage.
Keyword fallback can be added without touching this module.
"""
from __future__ import annotations

import time

import structlog

from app.adapters.vector import VectorStoreAdapter
from app.core.config import settings
from app.memory.embeddings import EmbeddingGenerator
from app.memory.models import Memory

logger = structlog.get_logger(__name__)


class MemoryRetriever:
    """
    Retrieves the most semantically relevant memories for a given query.

    Uses vector similarity as the primary retrieval mechanism.
    Only memories above the similarity threshold are returned.
    """

    def __init__(self, vector_store: VectorStoreAdapter, embedder: EmbeddingGenerator) -> None:
        self._vector = vector_store
        self._embedder = embedder

    async def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[Memory]:
        """
        Embed the query, perform vector search, and filter by threshold.

        Returns up to top_k memories whose similarity meets the threshold.
        """
        k = top_k or settings.TOP_K_RETRIEVAL
        sim_threshold = threshold or settings.SIMILARITY_THRESHOLD

        t0 = time.perf_counter()
        query_embedding = await self._embedder.embed(query)

        results = await self._vector.search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=k,
            threshold=sim_threshold,
        )

        logger.info(
            "retriever.retrieve.done",
            user_id=user_id,
            returned=len(results),
            top_k=k,
            threshold=sim_threshold,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return results
