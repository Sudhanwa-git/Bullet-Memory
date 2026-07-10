"""
Semantic Caching — bypass LLM inference for semantically identical queries.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
import chromadb

from app.core.config import settings
from app.memory.embeddings import EmbeddingGenerator

logger = structlog.get_logger(__name__)


class SemanticCache:
    """
    Ultra-low latency semantic caching layer. 
    Stores query embeddings and their corresponding LLM responses.
    If an incoming query matches a cached query's embedding with high similarity (e.g. >0.95),
    it immediately returns the cached response.
    """
    
    def __init__(self, embedder: EmbeddingGenerator, threshold: float = 0.95):
        self._embedder = embedder
        self._threshold = threshold
        
        chroma_host = getattr(settings, "CHROMA_HOST", "") or ""
        if chroma_host:
            chroma_port = int(getattr(settings, "CHROMA_PORT", 8000) or 8000)
            self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        else:
            self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            
        self._collection = self._client.get_or_create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"},
        )

    async def get(self, user_id: str, query: str) -> dict[str, Any] | None:
        """Return cached response payload if a highly similar query exists."""
        if self._collection.count() == 0:
            return None
            
        query_embedding = await self._embedder.embed(query)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where={"user_id": user_id},
        )
        
        distances = result.get("distances", [[]])[0]
        if not distances:
            return None
            
        similarity = 1.0 - distances[0]
        if similarity >= self._threshold:
            logger.info("semantic_cache.hit", user_id=user_id, similarity=round(similarity, 3))
            meta = result.get("metadatas", [[{}]])[0][0]
            payload_str = meta.get("payload")
            if payload_str:
                return json.loads(payload_str)
        return None

    async def set(self, user_id: str, query: str, response_payload: dict[str, Any]) -> None:
        """Cache the query and its LLM response payload."""
        try:
            query_embedding = await self._embedder.embed(query)
            payload_str = json.dumps(response_payload)
            self._collection.upsert(
                ids=[str(uuid.uuid4())],
                embeddings=[query_embedding],
                documents=[query],
                metadatas=[{"user_id": user_id, "payload": payload_str}],
            )
            logger.debug("semantic_cache.set", user_id=user_id)
        except Exception as e:
            logger.error("semantic_cache.set_error", error=str(e))
