"""
Chat endpoint — the primary user-facing API for memory-augmented LLM responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_orchestrator
from app.core.orchestrator import MemoryOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Request / Response schemas ────────────────────────────────────────────────


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique identifier for the user/agent")
    message: str = Field(..., min_length=1, description="The user's message")
    system_prompt: str | None = Field(default=None, description="Optional custom system prompt")


class ChatResponse(BaseModel):
    response: str
    memories_retrieved: int
    retrieved_context: list[dict[str, Any]] = []
    memories_stored: int | None = None
    latency_ms: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", summary="Send a memory-augmented chat message (Synchronous JSON)")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    orchestrator: MemoryOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """
    Standard JSON chat endpoint. Returns LLM response instantly, 
    and handles all memory extraction in the background.
    """
    try:
        result = await orchestrator.chat(
            user_id=request.user_id,
            message=request.message,
            system_prompt=request.system_prompt,
        )
        
        background_tasks.add_task(
            orchestrator.process_memory_background,
            user_id=request.user_id,
            message=request.message,
            response_text=result["response"],
        )
        
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stream", summary="Send a memory-augmented chat message via SSE stream")
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    orchestrator: MemoryOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """
    Streaming chat endpoint. Yields retrieved context and tokens in real-time.
    """
    try:
        return StreamingResponse(
            orchestrator.chat_stream(
                user_id=request.user_id,
                message=request.message,
                system_prompt=request.system_prompt,
                background_tasks=background_tasks,
            ),
            media_type="text/event-stream",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
