"""
Memory CRUD, search, and fine-tuning export endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.api.deps import get_memory_service
from app.memory.models import Memory, MemoryCategory, SourceType
from app.memory.service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


# ── Response schemas ──────────────────────────────────────────────────────────


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    agent_id: str | None
    session_id: str | None
    category: str
    source_type: str
    content: str
    source_text: str | None
    importance: float
    confidence: float
    tags: list[str]
    access_count: int
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    last_accessed_at: str | None

    @classmethod
    def from_memory(cls, m: Memory) -> MemoryResponse:
        return cls(
            id=m.id,
            user_id=m.user_id,
            agent_id=m.agent_id,
            session_id=m.session_id,
            category=m.category.value,
            source_type=m.source_type.value,
            content=m.content,
            source_text=m.source_text,
            importance=m.importance,
            confidence=m.confidence,
            tags=m.tags,
            access_count=m.access_count,
            metadata=m.metadata,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
            last_accessed_at=m.last_accessed_at.isoformat() if m.last_accessed_at else None,
        )


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int


class SearchRequest(BaseModel):
    user_id: str
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)


class MemoryUpdateRequest(BaseModel):
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ── CRUD Endpoints ────────────────────────────────────────────────────────────


@router.get(
    "/{user_id}", response_model=MemoryListResponse, summary="List memories with optional filters"
)
async def list_memories(
    user_id: str,
    agent_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    min_importance: float = Query(default=0.0, ge=0.0, le=1.0),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryListResponse:
    """
    Retrieve memories with powerful filtering:
    - Filter by agent_id to see what a specific agent has learned
    - Filter by session_id to reconstruct a session's context
    - Filter by source_type (chat, agent_event, tool_call, manual)
    - Filter by category and importance threshold
    """
    src_type = SourceType(source_type) if source_type else None
    cat = MemoryCategory(category) if category else None
    memories = await service.get_all(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        source_type=src_type,
        category=cat,
        min_importance=min_importance,
    )
    return MemoryListResponse(
        memories=[MemoryResponse.from_memory(m) for m in memories],
        total=len(memories),
    )


@router.get("/detail/{memory_id}", response_model=MemoryResponse, summary="Get a single memory")
async def get_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    memory = await service.get(memory_id=memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id!r} not found")
    return MemoryResponse.from_memory(memory)


@router.delete("/{memory_id}", summary="Delete a memory")
async def delete_memory(
    memory_id: str,
    service: MemoryService = Depends(get_memory_service),
) -> dict:
    deleted = await service.delete(memory_id=memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id!r} not found")
    return {"deleted": True, "memory_id": memory_id}


@router.put("/{memory_id}", response_model=MemoryResponse, summary="Update an existing memory")
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    # We update DB directly via service internal access for this simple case,
    # or expose an update method on MemoryService. Let's assume service._db has update_memory
    memory = await service._db.update_memory(
        memory_id=memory_id,
        content=request.content,
        importance=request.importance,
        confidence=request.confidence,
    )
    # Also update vector store
    import asyncio

    embedding = await service._embedder.embed(memory.content)
    asyncio.create_task(service._vector_store.update(memory, embedding))

    return MemoryResponse.from_memory(memory)


@router.post("/search", response_model=MemoryListResponse, summary="Semantic search over memories")
async def search_memories(
    request: SearchRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryListResponse:
    memories = await service.search(
        user_id=request.user_id,
        query=request.query,
        top_k=request.top_k,
    )
    return MemoryListResponse(
        memories=[MemoryResponse.from_memory(m) for m in memories],
        total=len(memories),
    )


# ── Fine-Tuning Export Endpoints ──────────────────────────────────────────────


@router.get(
    "/export/{user_id}",
    response_class=PlainTextResponse,
    summary="Export memories as JSONL fine-tuning dataset",
    tags=["export"],
)
async def export_memories(
    user_id: str,
    format: str = Query(default="openai", description="openai | instruction | jsonl"),
    min_importance: float = Query(default=0.6, ge=0.0, le=1.0),
    session_id: str | None = Query(default=None),
    service: MemoryService = Depends(get_memory_service),
) -> PlainTextResponse:
    """
    Export all memories as a fine-tuning dataset.

    Formats:
    - **openai**: OpenAI chat fine-tuning format ({"messages": [...]})
    - **instruction**: HuggingFace instruction-following format
    - **jsonl**: Raw JSONL with all memory fields

    Returns a plain JSONL file — download directly and use with your fine-tuning pipeline.
    """
    if format not in ("openai", "instruction", "jsonl"):
        raise HTTPException(
            status_code=400, detail=f"Invalid format {format!r}. Use: openai | instruction | jsonl"
        )

    records = await service.export_dataset(
        user_id=user_id,
        format=format,  # type: ignore
        min_importance=min_importance,
        session_id=session_id,
    )
    jsonl = service.serialize_dataset(records)
    filename = f"bullet_memory_{user_id}_{format}.jsonl"
    return PlainTextResponse(
        content=jsonl,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
