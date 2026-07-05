"""
Memory Service — the heart of the application.

All memory operations pass through this service.
External callers (orchestrator, API handlers) should never touch adapters directly.

Enhanced to support:
  - Multi-source ingestion (chat, agent_event, tool_call, manual)
  - Session-level grouping
  - Access count tracking
  - Fine-tuning dataset export
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.adapters.database import DatabaseAdapter
from app.adapters.vector import VectorStoreAdapter
from app.memory.embeddings import EmbeddingGenerator
from app.memory.exporter import ExportFormat, FineTuneExporter
from app.memory.extractor import MemoryExtractor
from app.memory.models import (
    AgentEventRequest,
    DirectMemoryRequest,
    ExtractedMemory,
    FineTuneRecord,
    Memory,
    MemoryCategory,
    SourceType,
)
from app.memory.retriever import MemoryRetriever
from app.memory.scorer import ImportanceScorer
from app.memory.updater import MemoryUpdater

logger = structlog.get_logger(__name__)


class MemoryService:
    """
    Facade that owns the complete memory lifecycle:

        Extract → Score → Embed → Deduplicate → Persist
        Retrieve → Enrich context → Track access
        Export → Fine-tuning datasets
    """

    def __init__(
        self,
        extractor: MemoryExtractor,
        scorer: ImportanceScorer,
        embedder: EmbeddingGenerator,
        retriever: MemoryRetriever,
        updater: MemoryUpdater,
        db: DatabaseAdapter,
        vector_store: VectorStoreAdapter,
    ) -> None:
        self._extractor = extractor
        self._scorer = scorer
        self._embedder = embedder
        self._retriever = retriever
        self._updater = updater
        self._db = db
        self._vector_store = vector_store
        self._exporter = FineTuneExporter(db)

    # ── Primary Ingestion Pipelines ───────────────────────────────────────────

    async def process_conversation(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> int:
        """
        Full post-inference memory pipeline for chat turns.
        Returns the number of new memories stored.
        """
        source_text = f"User: {user_message}\n\nAssistant: {assistant_response}"
        return await self._extract_and_store(
            user_id=user_id,
            user_message=user_message,
            assistant_response=assistant_response,
            source_text=source_text,
            source_type=SourceType.CHAT,
            agent_id=agent_id,
            session_id=session_id,
        )

    async def process_raw(
        self,
        user_id: str,
        text: str,
        source_type: SourceType = SourceType.API_INGEST,
        agent_id: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """
        Ingest any raw text string — extract memories from it.
        Used by the /ingest/raw API endpoint.
        """
        # Feed the raw text as both user message and context for extraction
        return await self._extract_and_store(
            user_id=user_id,
            user_message=text,
            assistant_response="",
            source_text=text,
            source_type=source_type,
            agent_id=agent_id,
            session_id=session_id,
            extra_tags=tags or [],
        )

    async def process_agent_event(self, request: AgentEventRequest) -> Memory:
        """
        Directly store a structured agent event as a memory.
        No LLM extraction — importance is caller-specified.
        """
        # Map event_type to MemoryCategory
        category_map = {
            "tool_call": MemoryCategory.TOOL_RESULT,
            "observation": MemoryCategory.AGENT_OBSERVATION,
            "reflection": MemoryCategory.FINE_TUNE_CANDIDATE,
            "instruction": MemoryCategory.INSTRUCTION,
        }
        category = category_map.get(request.event_type, MemoryCategory.SYSTEM_EVENT)

        candidate = ExtractedMemory(
            category=category,
            content=request.content,
            importance=request.importance,
            confidence=1.0,
            source_text=request.content,
            tags=request.tags,
        )

        embedding = await self._embedder.embed(candidate.content)
        memory, is_new = await self._updater.deduplicate_or_create(
            user_id=request.user_id,
            candidate=candidate,
            embedding=embedding,
            agent_id=request.agent_id,
            session_id=request.session_id,
            source_type=SourceType.AGENT_EVENT,
        )
        if is_new:
            await self._auto_export([memory])

        logger.info("memory_service.agent_event.done", user_id=request.user_id, is_new=is_new)
        return memory

    async def store_direct(self, request: DirectMemoryRequest) -> Memory:
        """
        Directly insert a pre-formed memory without LLM extraction.
        Useful for programmatic ingestion via the SDK.
        """
        now = datetime.now(UTC)
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id,
            category=request.category,
            source_type=request.source_type,
            content=request.content,
            importance=request.importance,
            confidence=request.confidence,
            tags=request.tags,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
        )
        embedding = await self._embedder.embed(memory.content)
        memory = await self._db.create_direct_memory(memory)
        await self._vector_store.upsert(
            memory_id=memory.id, user_id=memory.user_id, embedding=embedding, content=memory.content
        )

        await self._auto_export([memory])

        logger.info("memory_service.store_direct.done", memory_id=memory.id)
        return memory

    # ── Retrieval ─────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[Memory]:
        """Retrieve semantically relevant memories. Tracks access counts."""
        memories = await self._retriever.retrieve(
            user_id=user_id, query=query, top_k=top_k, threshold=threshold
        )
        import asyncio
        # Track access asynchronously (fire and forget via background — don't block retrieval)
        for m in memories:
            asyncio.create_task(self._db.increment_access_count(m.id))
        return memories

    async def get_all(
        self,
        user_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: SourceType | None = None,
        category: MemoryCategory | None = None,
        min_importance: float = 0.0,
    ) -> list[Memory]:
        """Return memories with optional filtering."""
        return await self._db.list_memories(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            source_type=source_type,
            category=category,
            min_importance=min_importance,
        )

    async def get(self, memory_id: str) -> Memory | None:
        return await self._db.get_memory(memory_id=memory_id)

    async def delete(self, memory_id: str) -> bool:
        memory = await self._db.get_memory(memory_id)
        if not memory:
            return False
        await self._db.delete_memory(memory_id)
        await self._vector_store.delete(memory_id)
        logger.info("memory_service.delete", memory_id=memory_id)
        return True

    async def search(self, user_id: str, query: str, top_k: int = 10) -> list[Memory]:
        """Semantic search without similarity threshold."""
        return await self._retriever.retrieve(
            user_id=user_id, query=query, top_k=top_k, threshold=0.0
        )

    # ── Export ────────────────────────────────────────────────────────────────

    async def export_dataset(
        self,
        user_id: str,
        format: ExportFormat = "openai",
        min_importance: float = 0.6,
        session_id: str | None = None,
    ) -> list[FineTuneRecord]:
        """Export memories as a fine-tuning dataset."""
        return await self._exporter.export(
            user_id=user_id,
            format=format,
            min_importance=min_importance,
            session_id=session_id,
        )

    def serialize_dataset(self, records: list[FineTuneRecord]) -> str:
        """Convert fine-tuning records to JSONL string."""
        return self._exporter.to_jsonl_string(records)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _extract_and_store(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        source_text: str,
        source_type: SourceType,
        agent_id: str | None = None,
        session_id: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> int:
        candidates: list[ExtractedMemory] = await self._extractor.extract(
            user_message=user_message,
            assistant_response=assistant_response,
            source_text=source_text,
        )

        accepted = self._scorer.filter(candidates)
        if not accepted:
            logger.info("memory_service.pipeline.nothing_accepted", user_id=user_id)
            return 0

        # Inject tags
        if extra_tags:
            for c in accepted:
                c.tags = list(set(c.tags + extra_tags))

        stored = 0
        new_memories = []
        
        import asyncio
        
        async def process_candidate(candidate):
            embedding = await self._embedder.embed(candidate.content)
            memory, is_new = await self._updater.deduplicate_or_create(
                user_id=user_id,
                candidate=candidate,
                embedding=embedding,
                agent_id=agent_id,
                session_id=session_id,
                source_type=source_type,
            )
            return memory, is_new

        results = await asyncio.gather(*(process_candidate(c) for c in accepted))
        
        for memory, is_new in results:
            if is_new:
                stored += 1
                new_memories.append(memory)

        if new_memories:
            await self._auto_export(new_memories)

        logger.info("memory_service.pipeline.done", user_id=user_id, stored=stored)
        return stored

    async def _auto_export(self, memories: list[Memory]) -> None:
        """Automatically append new memories to a JSONL dataset in the background."""
        import asyncio
        import json
        from pathlib import Path

        async def _write():
            for m in memories:
                # We'll use the generic OpenAI format for the auto-dataset
                record = self._exporter._to_openai_record(m)

                # Use a central datasets directory
                dataset_dir = Path("datasets")
                dataset_dir.mkdir(exist_ok=True)

                file_path = dataset_dir / f"{m.user_id}_finetune.jsonl"
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")

        # Fire and forget
        asyncio.create_task(_write())
