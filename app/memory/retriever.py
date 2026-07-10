"""
Memory Retriever — semantic search over the vector store.

Retrieval is intentionally separate from storage.
Keyword fallback can be added without touching this module.
"""

from __future__ import annotations

import time

import structlog

from app.adapters.vector import VectorStoreAdapter
from app.adapters.database import DatabaseAdapter
from app.core.config import settings
from app.memory.embeddings import EmbeddingGenerator
from app.memory.models import Memory
from datetime import datetime, UTC
import math

logger = structlog.get_logger(__name__)


class MemoryRetriever:
    """
    Retrieves the most semantically relevant memories for a given query.

    Uses vector similarity as the primary retrieval mechanism.
    Only memories above the similarity threshold are returned.
    """

    def __init__(self, vector_store: VectorStoreAdapter, embedder: EmbeddingGenerator, db: DatabaseAdapter) -> None:
        self._vector = vector_store
        self._embedder = embedder
        self._db = db

    def _calculate_time_decay(self, memory: Memory) -> float:
        """Applies a time decay factor based on created_at or last_accessed_at."""
        reference_time = memory.last_accessed_at or memory.created_at
        if not reference_time:
            return 1.0
        
        # Calculate days ago
        delta = datetime.now(UTC) - reference_time.replace(tzinfo=UTC)
        days_ago = delta.total_seconds() / (24 * 3600)
        
        # Simple exponential decay formula
        # Half-life of 30 days
        decay_factor = math.pow(0.5, days_ago / 30.0)
        return max(0.1, decay_factor) # minimum weight of 0.1

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

        # 1. Semantic Search
        query_embedding = await self._embedder.embed(query)
        vector_results = await self._vector.search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=k * 2, # Fetch more to re-rank
            threshold=sim_threshold,
        )

        # 2. Lexical Search (Hybrid Fallback)
        lexical_results = await self._db.search_memories_text(user_id=user_id, query=query)
        
        # 3. Combine and Deduplicate
        combined: dict[str, Memory] = {}
        for m in vector_results:
            combined[m.id] = m
        for m in lexical_results:
            if m.id not in combined:
                combined[m.id] = m
                
        # 4. Contextual & Time-Weighted Re-ranking
        # For a truly robust system, we'd use a Cross-Encoder here.
        # For now, we apply a time-weight penalty to the results and sort by importance * decay.
        scored_memories = []
        for m in combined.values():
            decay = self._calculate_time_decay(m)
            # We mix base importance with time decay
            final_score = m.importance * decay
            scored_memories.append((final_score, m))
            
        # Sort descending by final score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        final_results = [m for _, m in scored_memories[:k]]

        # 5. Fetch Multi-Hop Graph Context
        final_memory_ids = [m.id for m in final_results]
        graph_triples = await self._db.get_graph_context_for_memories(final_memory_ids)
        
        if graph_triples:
            import uuid
            from app.memory.models import MemoryCategory, SourceType
            now = datetime.now(UTC)
            for triple in graph_triples:
                graph_mem = Memory(
                    id=f"graph-{uuid.uuid4()}",
                    user_id=user_id,
                    category=MemoryCategory.AGENT_OBSERVATION,
                    source_type=SourceType.AGENT_EVENT,
                    content=f"[Graph Knowledge] {triple}",
                    importance=0.5,
                    confidence=1.0,
                    created_at=now,
                    updated_at=now,
                )
                final_results.append(graph_mem)

        logger.info(
            "retriever.retrieve.done",
            user_id=user_id,
            returned=len(final_results),
            top_k=k,
            threshold=sim_threshold,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return final_results

