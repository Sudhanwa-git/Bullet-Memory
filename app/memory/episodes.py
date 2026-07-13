"""
Episode & Reflection Engine — Turn every execution into a learning opportunity.

Episode Engine:
  Records every significant agent interaction as a complete, replayable episode.
  An episode captures the goal, timeline of events, outcomes, and lessons.

Reflection Engine:
  After an episode completes, automatically analyzes it using an LLM to extract:
  - What worked
  - What failed and why
  - Reusable procedural knowledge (playbooks)
  - Lessons stored as high-importance Semantic Memories

This is the system that transforms Bullet Memory from a retrieval tool into a
continuously improving cognitive system.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from app.adapters.llm import LLMAdapter

logger = structlog.get_logger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────


class EpisodeStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    REFLECTED = "reflected"


class EpisodeEvent:
    """A single timestamped event within an episode."""

    def __init__(
        self, event_type: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type  # e.g. "tool_call", "observation", "step_complete", "error"
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class Episode:
    """
    A complete, replayable execution record.
    Every agent run should create one episode.
    """

    def __init__(
        self,
        episode_id: str,
        session_id: str,
        user_id: str,
        agent_id: str,
        goal: str,
    ) -> None:
        self.episode_id = episode_id
        self.session_id = session_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.goal = goal
        self.status = EpisodeStatus.ACTIVE
        self.timeline: list[EpisodeEvent] = []
        self.outcome: str = ""
        self.reflection: str = ""
        self.lessons: list[str] = []
        self.started_at = datetime.now(UTC).isoformat()
        self.ended_at: str | None = None

    def add_event(self, event_type: str, content: str, metadata: dict | None = None) -> None:
        self.timeline.append(EpisodeEvent(event_type, content, metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "goal": self.goal,
            "status": self.status,
            "timeline": [e.to_dict() for e in self.timeline],
            "outcome": self.outcome,
            "reflection": self.reflection,
            "lessons": self.lessons,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }

    def to_narrative(self) -> str:
        """Convert episode to a human-readable narrative for reflection."""
        parts = [f"GOAL: {self.goal}", f"STATUS: {self.status}", "TIMELINE:"]
        for e in self.timeline:
            parts.append(f"  [{e.event_type.upper()}] {e.content}")
        if self.outcome:
            parts.append(f"OUTCOME: {self.outcome}")
        return "\n".join(parts)


# ── Episode Engine ────────────────────────────────────────────────────────────


class EpisodeEngine:
    """
    Records and manages agent execution episodes.

    Hot-stores active episodes in memory for zero-latency event logging.
    Persists completed episodes to SQLite for long-term analysis.
    """

    def __init__(self) -> None:
        # In-memory store of active episodes: episode_id -> Episode
        self._active: dict[str, Episode] = {}

    def create(
        self,
        session_id: str,
        user_id: str,
        agent_id: str,
        goal: str,
    ) -> Episode:
        """Start a new episode. Call this at the beginning of any agent run."""
        episode_id = str(uuid.uuid4())
        episode = Episode(
            episode_id=episode_id,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            goal=goal,
        )
        self._active[episode_id] = episode
        logger.info("episode.created", episode_id=episode_id, goal=goal)
        return episode

    def log_event(
        self,
        episode_id: str,
        event_type: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Log an event to the active episode. Zero-latency (in-memory only)."""
        episode = self._active.get(episode_id)
        if episode is None:
            logger.warning("episode.log_event.not_found", episode_id=episode_id)
            return
        episode.add_event(event_type, content, metadata)

    def complete(self, episode_id: str, outcome: str) -> Episode | None:
        """Mark an episode as successfully completed."""
        episode = self._active.get(episode_id)
        if episode:
            episode.status = EpisodeStatus.COMPLETED
            episode.outcome = outcome
            episode.ended_at = datetime.now(UTC).isoformat()
            logger.info("episode.completed", episode_id=episode_id)
        return episode

    def fail(self, episode_id: str, reason: str) -> Episode | None:
        """Mark an episode as failed."""
        episode = self._active.get(episode_id)
        if episode:
            episode.status = EpisodeStatus.FAILED
            episode.outcome = f"FAILED: {reason}"
            episode.ended_at = datetime.now(UTC).isoformat()
            logger.warning("episode.failed", episode_id=episode_id, reason=reason)
        return episode

    def get(self, episode_id: str) -> Episode | None:
        return self._active.get(episode_id)

    def evict(self, episode_id: str) -> None:
        """Remove from hot cache after reflection is done."""
        self._active.pop(episode_id, None)


# ── Reflection Engine ─────────────────────────────────────────────────────────


REFLECTION_PROMPT = """You are an expert at analyzing AI agent execution episodes to extract lessons.

Given the following episode, your task is to analyze what happened and produce:
1. A clear reflection on what worked and what failed
2. 2-5 concrete, reusable lessons for future runs

Respond ONLY in this exact JSON format:
{{
  "reflection": "A 2-3 sentence summary of what happened and why",
  "lessons": [
    "Lesson 1 as a concrete, actionable statement",
    "Lesson 2 as a concrete, actionable statement"
  ]
}}

EPISODE:
{narrative}
"""


class ReflectionEngine:
    """
    Analyzes completed episodes using an LLM to extract reusable knowledge.

    This runs entirely in the background — it never blocks the agent's
    primary request/response cycle. Reflections are stored as high-importance
    Semantic Memories so they inform future runs.
    """

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    async def reflect(self, episode: Episode) -> dict[str, Any]:
        """
        Reflect on a completed or failed episode.
        Returns the structured reflection with lessons learned.
        """
        if episode.status == EpisodeStatus.ACTIVE:
            logger.warning("reflection.skipped.still_active", episode_id=episode.episode_id)
            return {}

        narrative = episode.to_narrative()
        prompt = REFLECTION_PROMPT.format(narrative=narrative)

        logger.info("reflection.start", episode_id=episode.episode_id)
        try:
            raw = await self._llm.complete(
                system="You are a precise episode analyzer. Return only valid JSON.",
                user=prompt,
            )
            # Try to parse the JSON response
            result = json.loads(raw)
            episode.reflection = result.get("reflection", "")
            episode.lessons = result.get("lessons", [])
            episode.status = EpisodeStatus.REFLECTED
            logger.info(
                "reflection.done",
                episode_id=episode.episode_id,
                lessons_count=len(episode.lessons),
            )
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.error("reflection.error", episode_id=episode.episode_id, error=str(e))
            return {}

    async def reflect_background(self, episode: Episode, episode_engine: EpisodeEngine) -> None:
        """
        Runs reflection asynchronously without blocking the calling thread.
        After reflection, evicts the episode from hot cache to free memory.
        """
        await self.reflect(episode)
        episode_engine.evict(episode.episode_id)
