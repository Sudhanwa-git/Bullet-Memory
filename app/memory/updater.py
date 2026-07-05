"""
Memory Updater — maintains consistency inside the memory store.

If incoming knowledge contradicts or duplicates an existing memory,
the existing record is updated rather than duplicated.

The goal is one accurate representation of each fact.
"""
from __future__ import annotations

import structlog

from app.adapters.database import DatabaseAdapter
from app.adapters.vector import VectorStoreAdapter
from app.memory.embeddings import EmbeddingGenerator
from app.memory.models import ExtractedMemory, Memory, SourceType

logger = structlog.get_logger(__name__)

# Cosine similarity above this value is considered a duplicate
_DUPLICATE_THRESHOLD = 0.90


class MemoryUpdater:
    """
    Detects near-duplicate memories and merges them rather than creating duplicates.

    Duplicate detection uses vector similarity against the user's existing memories.
    """

    def __init__(
        self,
        db: DatabaseAdapter,
        vector_store: VectorStoreAdapter,
        embedder: EmbeddingGenerator,
    ) -> None:
        self._db = db
        self._vector = vector_store
        self._embedder = embedder

    async def deduplicate_or_create(
        self,
        user_id: str,
        candidate: ExtractedMemory,
        embedding: list[float],
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: SourceType = SourceType.CHAT,
    ) -> tuple[Memory, bool]:
        """
        Check if a near-duplicate already exists.

        Returns (memory, is_new):
        - If duplicate found: updates content/importance and returns (updated_memory, False)
        - If no duplicate: creates new memory and returns (new_memory, True)
        """
        # Search for near-duplicates in the same category
        similar = await self._vector.search(
            user_id=user_id,
            query_embedding=embedding,
            top_k=1,
            threshold=_DUPLICATE_THRESHOLD,
        )

        if similar:
            existing = similar[0]
            updated = await self._update(existing, candidate)
            logger.info(
                "updater.duplicate_merged",
                user_id=user_id,
                memory_id=existing.id,
                old=existing.content[:60],
                new=candidate.content[:60],
            )
            return updated, False

        # No duplicate — create fresh memory
        new_memory = await self._db.create_memory(
            user_id=user_id,
            candidate=candidate,
            embedding=embedding,
            agent_id=agent_id,
            session_id=session_id,
            source_type=source_type,
        )
        await self._vector.add(new_memory, embedding=embedding)
        logger.info("updater.memory_created", user_id=user_id, memory_id=new_memory.id)
        return new_memory, True

    async def _update(self, existing: Memory, candidate: ExtractedMemory) -> Memory:
        """
        Update an existing memory with new content if the incoming fact is newer/more confident.
        """
        # Prefer the higher-confidence or more descriptive version
        if candidate.confidence >= existing.confidence or len(candidate.content) > len(existing.content):
            updated = await self._db.update_memory(
                memory_id=existing.id,
                content=candidate.content,
                importance=max(existing.importance, candidate.importance),
                confidence=candidate.confidence,
            )
            # Re-embed and re-index
            new_embedding = await self._embedder.embed(candidate.content)
            await self._vector.update(updated, new_embedding)
            return updated
        return existing
