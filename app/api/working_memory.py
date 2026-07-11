"""
Working Memory API — Endpoints for managing ephemeral agent execution state.

These routes allow agents to:
- Create a new working memory session before starting a task
- Log events, tool outputs, and step completions in real-time
- Resume a crashed session from its last checkpoint
- Clean up after task completion
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.memory.working_memory import WorkingMemoryEngine, WorkingMemoryState

router = APIRouter(prefix="/working-memory", tags=["Working Memory"])

# Singleton engine (initialized once per process)
_engine: WorkingMemoryEngine | None = None


def get_engine() -> WorkingMemoryEngine:
    global _engine
    if _engine is None:
        _engine = WorkingMemoryEngine()
    return _engine


# ── Request Models ─────────────────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    session_id: str
    agent_id: str
    user_id: str
    goal: str = ""


class SetPlanRequest(BaseModel):
    plan: list[str] = Field(..., min_length=1)


class CompleteStepRequest(BaseModel):
    step: str


class SetVariableRequest(BaseModel):
    key: str
    value: Any


class ToolOutputRequest(BaseModel):
    tool: str
    output: Any


class UpdateScratchpadRequest(BaseModel):
    text: str


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/sessions", summary="Create a new working memory session")
async def create_session(req: CreateSessionRequest) -> dict:
    engine = get_engine()
    await engine.initialise()
    state = await engine.create(
        session_id=req.session_id,
        agent_id=req.agent_id,
        user_id=req.user_id,
        goal=req.goal,
    )
    return {"session_id": state.session_id, "status": "created", "checkpoint_id": state.checkpoint_id}


@router.get("/sessions/{session_id}", summary="Get or resume a working memory session")
async def get_session(session_id: str) -> dict:
    engine = get_engine()
    await engine.initialise()
    state = await engine.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return state.to_dict()


@router.post("/sessions/{session_id}/plan", summary="Set the agent's execution plan")
async def set_plan(session_id: str, req: SetPlanRequest) -> dict:
    engine = get_engine()
    await engine.initialise()
    try:
        await engine.set_plan(session_id, req.plan)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    state = await engine.get(session_id)
    return {"session_id": session_id, "plan": state.plan if state else [], "checkpoint_id": state.checkpoint_id if state else ""}


@router.post("/sessions/{session_id}/steps/complete", summary="Mark a step as completed")
async def complete_step(session_id: str, req: CompleteStepRequest) -> dict:
    engine = get_engine()
    try:
        await engine.complete_step(session_id, req.step)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    state = await engine.get(session_id)
    return {
        "session_id": session_id,
        "completed": state.completed_steps if state else [],
        "pending": state.pending_steps if state else [],
    }


@router.post("/sessions/{session_id}/variables", summary="Set a working memory variable")
async def set_variable(session_id: str, req: SetVariableRequest) -> dict:
    engine = get_engine()
    try:
        await engine.set_variable(session_id, req.key, req.value)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"session_id": session_id, "key": req.key, "status": "set"}


@router.post("/sessions/{session_id}/tool-outputs", summary="Log a tool call output")
async def add_tool_output(session_id: str, req: ToolOutputRequest) -> dict:
    engine = get_engine()
    try:
        await engine.add_tool_output(session_id, req.tool, req.output)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"session_id": session_id, "tool": req.tool, "status": "logged"}


@router.post("/sessions/{session_id}/scratchpad", summary="Update the reasoning scratchpad")
async def update_scratchpad(session_id: str, req: UpdateScratchpadRequest) -> dict:
    engine = get_engine()
    try:
        await engine.update_scratchpad(session_id, req.text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"session_id": session_id, "status": "updated"}


@router.delete("/sessions/{session_id}", summary="Delete a working memory session")
async def delete_session(session_id: str) -> dict:
    engine = get_engine()
    await engine.delete(session_id)
    return {"session_id": session_id, "status": "deleted"}
