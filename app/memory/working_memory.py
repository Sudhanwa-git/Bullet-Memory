"""
Working Memory Engine — Ephemeral execution state for AI agents.

This engine solves the critical reliability problem: if an agent crashes,
its entire reasoning context is lost and it cannot resume.

Working Memory tracks:
- Current goal
- Active plan (ordered steps)
- Completed & pending steps
- Intermediate variables / scratchpad
- Tool outputs
- Checkpoints (for crash recovery)

Every mutation is immediately persisted async to SQLite so the agent can
resume from any point with zero data loss.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ── ORM Row ───────────────────────────────────────────────────────────────────


class WorkingMemoryRow:
    """Lightweight SQLAlchemy core table (no ORM Base to avoid circular imports)."""
    __tablename__ = "working_memory"


# ── Models ────────────────────────────────────────────────────────────────────


class WorkingMemoryState:
    """
    In-memory snapshot of an agent's working memory.
    Serializes to JSON for SQLite persistence.
    """

    def __init__(
        self,
        session_id: str,
        agent_id: str,
        user_id: str,
        goal: str = "",
    ) -> None:
        self.session_id = session_id
        self.agent_id = agent_id
        self.user_id = user_id
        self.goal = goal
        self.plan: list[str] = []
        self.completed_steps: list[str] = []
        self.pending_steps: list[str] = []
        self.variables: dict[str, Any] = {}
        self.tool_outputs: list[dict[str, Any]] = []
        self.scratchpad: str = ""
        self.checkpoint_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now(UTC)
        self.updated_at: datetime = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "goal": self.goal,
            "plan": self.plan,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "variables": self.variables,
            "tool_outputs": self.tool_outputs,
            "scratchpad": self.scratchpad,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkingMemoryState":
        state = cls(
            session_id=data["session_id"],
            agent_id=data["agent_id"],
            user_id=data["user_id"],
            goal=data.get("goal", ""),
        )
        state.plan = data.get("plan", [])
        state.completed_steps = data.get("completed_steps", [])
        state.pending_steps = data.get("pending_steps", [])
        state.variables = data.get("variables", {})
        state.tool_outputs = data.get("tool_outputs", [])
        state.scratchpad = data.get("scratchpad", "")
        state.checkpoint_id = data.get("checkpoint_id", str(uuid.uuid4()))
        return state


# ── Engine ────────────────────────────────────────────────────────────────────


class WorkingMemoryEngine:
    """
    Manages ephemeral execution state for AI agents.

    Provides fast in-memory access (dict lookup) with async SQLite persistence
    so state survives crashes and process restarts.

    Usage:
        engine = WorkingMemoryEngine()
        await engine.initialise()

        state = await engine.create(session_id, agent_id, user_id, goal="Deploy service")
        await engine.set_plan(session_id, ["Build", "Test", "Push", "Deploy"])
        await engine.complete_step(session_id, "Build")
        await engine.set_variable(session_id, "build_output", "SUCCESS")

        # Agent crashes -> on restart:
        state = await engine.resume(session_id)  # Full state restored!
    """

    def __init__(self) -> None:
        self._engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False
        )
        # Hot cache: session_id -> WorkingMemoryState
        self._cache: dict[str, WorkingMemoryState] = {}

    async def initialise(self) -> None:
        """Create the working_memory table if it doesn't exist."""
        async with self._engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS working_memory (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """))
        logger.info("working_memory.initialised")

    async def create(
        self,
        session_id: str,
        agent_id: str,
        user_id: str,
        goal: str = "",
    ) -> WorkingMemoryState:
        """Create a new working memory session."""
        state = WorkingMemoryState(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            goal=goal,
        )
        self._cache[session_id] = state
        await self._persist(state)
        logger.info("working_memory.created", session_id=session_id, goal=goal)
        return state

    async def get(self, session_id: str) -> WorkingMemoryState | None:
        """Get current state from cache or SQLite."""
        if session_id in self._cache:
            return self._cache[session_id]
        return await self.resume(session_id)

    async def resume(self, session_id: str) -> WorkingMemoryState | None:
        """Restore working memory from SQLite after a crash or restart."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("SELECT state_json FROM working_memory WHERE session_id = :sid").bindparams(sid=session_id)
            )
            row = result.fetchone()
        if row is None:
            return None
        state = WorkingMemoryState.from_dict(json.loads(row[0]))
        self._cache[session_id] = state
        logger.info("working_memory.resumed", session_id=session_id)
        return state

    async def set_plan(self, session_id: str, plan: list[str]) -> None:
        """Set the agent's execution plan."""
        state = await self._require(session_id)
        state.plan = list(plan)
        state.pending_steps = list(plan)
        state.completed_steps = []
        await self._checkpoint(state)

    async def complete_step(self, session_id: str, step: str) -> None:
        """Mark a step as completed and move to next pending step."""
        state = await self._require(session_id)
        if step in state.pending_steps:
            state.pending_steps.remove(step)
        if step not in state.completed_steps:
            state.completed_steps.append(step)
        await self._checkpoint(state)
        logger.debug("working_memory.step_completed", session_id=session_id, step=step)

    async def set_variable(self, session_id: str, key: str, value: Any) -> None:
        """Store an intermediate variable in the scratchpad."""
        state = await self._require(session_id)
        state.variables[key] = value
        await self._checkpoint(state)

    async def add_tool_output(self, session_id: str, tool: str, output: Any) -> None:
        """Append a tool call result to the working memory."""
        state = await self._require(session_id)
        state.tool_outputs.append({
            "tool": tool,
            "output": output,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        await self._checkpoint(state)

    async def update_scratchpad(self, session_id: str, text: str) -> None:
        """Update the agent's free-form reasoning scratchpad."""
        state = await self._require(session_id)
        state.scratchpad = text
        await self._checkpoint(state)

    async def delete(self, session_id: str) -> None:
        """Clean up a completed session."""
        self._cache.pop(session_id, None)
        async with self._session_factory() as session:
            await session.execute(
                text("DELETE FROM working_memory WHERE session_id = :sid").bindparams(sid=session_id)
            )
            await session.commit()
        logger.info("working_memory.deleted", session_id=session_id)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _require(self, session_id: str) -> WorkingMemoryState:
        state = await self.get(session_id)
        if state is None:
            raise ValueError(f"No working memory found for session '{session_id}'")
        return state

    async def _checkpoint(self, state: WorkingMemoryState) -> None:
        """Persist state change immediately (low-latency checkpoint)."""
        state.updated_at = datetime.now(UTC)
        state.checkpoint_id = str(uuid.uuid4())
        await self._persist(state)

    async def _persist(self, state: WorkingMemoryState) -> None:
        """Upsert the state to SQLite."""
        data = state.to_dict()
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO working_memory 
                        (session_id, agent_id, user_id, state_json, checkpoint_id, created_at, updated_at)
                    VALUES 
                        (:sid, :aid, :uid, :json, :cid, :cat, :uat)
                    ON CONFLICT(session_id) DO UPDATE SET
                        state_json = :json,
                        checkpoint_id = :cid,
                        updated_at = :uat
                """).bindparams(
                    sid=state.session_id,
                    aid=state.agent_id,
                    uid=state.user_id,
                    json=json.dumps(data),
                    cid=state.checkpoint_id,
                    cat=data["created_at"],
                    uat=data["updated_at"],
                )
            )
            await session.commit()
