"""
Vector Store Adapter — provider-agnostic interface for semantic search.

Supports ChromaDB (persistent) and an in-memory fallback for testing.
Swap providers by implementing VectorStoreAdapter and updating get_vector_store().
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from app.core.config import settings
from app.memory.models import Memory

logger = structlog.get_logger(__name__)


# ── Abstract interface ────────────────────────────────────────────────────────

class VectorStoreAdapter(ABC):
    @abstractmethod
    async def add(self, memory: Memory, embedding: list[float] | None = None) -> None:
        """Index a memory. If embedding is None, use memory.embedding."""

    @abstractmethod
    async def update(self, memory: Memory, embedding: list[float]) -> None:
        """Update an existing memory's vector."""

    @abstractmethod
    async def delete(self, memory_id: str) -> None:
        """Remove a memory from the index."""

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
    ) -> list[Memory]:
        """Return top_k memories above the similarity threshold."""


# ── ChromaDB Implementation ───────────────────────────────────────────────────

class ChromaVectorStore(VectorStoreAdapter):
    _COLLECTION_NAME = "bullet_memories"

    def __init__(self) -> None:
        import chromadb
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, memory: Memory, embedding: list[float] | None = None) -> None:
        vec = embedding or memory.embedding
        if not vec:
            raise ValueError("Cannot index memory without an embedding")
        self._collection.upsert(
            ids=[memory.id],
            embeddings=[vec],
            documents=[memory.content],
            metadatas=[{"user_id": memory.user_id, "category": memory.category.value}],
        )

    async def update(self, memory: Memory, embedding: list[float]) -> None:
        await self.add(memory, embedding)

    async def delete(self, memory_id: str) -> None:
        self._collection.delete(ids=[memory_id])

    async def search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
    ) -> list[Memory]:
        from app.adapters.database import DatabaseAdapter

        # ChromaDB raises if n_results > collection count
        collection_count = self._collection.count()
        if collection_count == 0:
            return []
        n_results = min(top_k, collection_count)

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"user_id": user_id},
        )

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]

        memories: list[Memory] = []
        db = _get_db()

        for mem_id, distance in zip(ids, distances):
            similarity = 1.0 - distance  # ChromaDB cosine: distance = 1 - similarity
            if similarity >= threshold:
                memory = await db.get_memory(mem_id)
                if memory:
                    memories.append(memory)

        return memories


# ── In-Memory Implementation (testing / CI) ───────────────────────────────────

class InMemoryVectorStore(VectorStoreAdapter):
    """
    Pure Python cosine-similarity store.
    NOT suitable for production — use for unit tests only.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Memory, list[float]]] = {}

    async def add(self, memory: Memory, embedding: list[float] | None = None) -> None:
        vec = embedding or memory.embedding or []
        self._store[memory.id] = (memory, vec)

    async def update(self, memory: Memory, embedding: list[float]) -> None:
        await self.add(memory, embedding)

    async def delete(self, memory_id: str) -> None:
        self._store.pop(memory_id, None)

    async def search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
    ) -> list[Memory]:
        import numpy as np

        q = np.array(query_embedding, dtype=float)
        scores: list[tuple[float, Memory]] = []

        for memory, vec in self._store.values():
            if memory.user_id != user_id:
                continue
            v = np.array(vec, dtype=float)
            norm = np.linalg.norm(q) * np.linalg.norm(v)
            similarity = float(np.dot(q, v) / norm) if norm > 0 else 0.0
            if similarity >= threshold:
                scores.append((similarity, memory))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scores[:top_k]]


# ── Lazy DB singleton (avoids circular imports) ───────────────────────────────

_db_instance: "DatabaseAdapter | None" = None  # type: ignore[name-defined]


def _get_db():  # type: ignore[return]
    global _db_instance
    if _db_instance is None:
        from app.adapters.database import DatabaseAdapter
        _db_instance = DatabaseAdapter()
    return _db_instance


# ── Factory ───────────────────────────────────────────────────────────────────

def get_vector_store() -> VectorStoreAdapter:
    provider = settings.VECTOR_STORE_PROVIDER.lower()
    if provider == "chroma":
        return ChromaVectorStore()
    if provider == "in_memory":
        return InMemoryVectorStore()
    raise ValueError(f"Unsupported vector store: {provider!r}. Add it to adapters/vector.py")
