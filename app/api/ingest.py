"""
Ingest API — pluggable memory ingestion for any agent, tool, or system.

Endpoints:
  POST /ingest/raw        — Push raw text and extract memories from it
  POST /ingest/event      — Push a structured agent event (tool_call, observation, etc.)
  POST /ingest/direct     — Directly insert pre-formed memories (no LLM extraction)

This is the primary interface for external agents to feed data into Bullet Memory.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import get_memory_service
from app.memory.models import AgentEventRequest, DirectMemoryRequest, RawIngestRequest
from app.memory.service import MemoryService

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── Raw text ingestion ────────────────────────────────────────────────────────

@router.post("/raw", summary="Ingest raw text and extract memories from it")
async def ingest_raw(
    request: RawIngestRequest,
    background_tasks: BackgroundTasks,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    """
    Push any raw text string — conversations, documents, agent outputs, logs.
    Bullet Memory will extract high-signal, durable facts from it in the background.

    Ideal for:
      - Ingesting agent observations and reflections
      - Feeding conversation logs from external systems
      - Batch-loading historical data
    """
    async def _run():
        stored = await service.process_raw(
            user_id=request.user_id,
            text=request.text,
            source_type=request.source_type,
            agent_id=request.agent_id,
            session_id=request.session_id,
            tags=request.tags,
        )
        return stored

    background_tasks.add_task(_run)
    return {
        "status": "accepted",
        "message": "Raw text queued for memory extraction.",
        "user_id": request.user_id,
        "source_type": request.source_type,
    }


@router.post("/raw/sync", summary="Ingest raw text (synchronous — waits for extraction)")
async def ingest_raw_sync(
    request: RawIngestRequest,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    """
    Synchronous version of /ingest/raw.
    Waits for LLM extraction and returns the number of memories stored.
    Use this when you need to confirm storage before proceeding.
    """
    try:
        stored = await service.process_raw(
            user_id=request.user_id,
            text=request.text,
            source_type=request.source_type,
            agent_id=request.agent_id,
            session_id=request.session_id,
            tags=request.tags,
        )
        return {
            "status": "success",
            "memories_stored": stored,
            "user_id": request.user_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Agent event ingestion ─────────────────────────────────────────────────────

@router.post("/event", summary="Push a structured agent event as a memory")
async def ingest_event(
    request: AgentEventRequest,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    """
    Store a structured agent event directly.
    No LLM extraction — the content IS the memory.

    Ideal for:
      - Tool call results (e.g. code execution outputs)
      - Agent observations (e.g. "User clicked on Python docs 5 times")
      - Reflections and self-notes from autonomous agents
    """
    try:
        memory = await service.process_agent_event(request)
        return {
            "status": "success",
            "memory_id": memory.id,
            "category": memory.category.value,
            "content": memory.content,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Direct memory insertion ───────────────────────────────────────────────────

@router.post("/direct", summary="Directly insert a pre-formed memory")
async def ingest_direct(
    request: DirectMemoryRequest,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    """
    Insert a pre-formed memory directly without LLM extraction.
    Caller is fully responsible for content quality and importance scoring.

    Ideal for:
      - SDK users who want full control
      - Migrating memories from another system
      - High-frequency programmatic ingestion where LLM extraction is too slow
    """
    try:
        memory = await service.store_direct(request)
        return {
            "status": "success",
            "memory_id": memory.id,
            "category": memory.category.value,
            "content": memory.content,
            "importance": memory.importance,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
