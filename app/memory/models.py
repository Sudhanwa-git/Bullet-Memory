"""
Core data models for the Bullet Memory Engine.

These are the canonical representations used across the entire application.
The schema is intentionally rich to support:
  - Multi-agent ingestion (not just chat)
  - Fine-tuning dataset export
  - Session-level context grouping
  - Memory access tracking for relevance weighting
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Enumerations ──────────────────────────────────────────────────────────────


class MemoryCategory(StrEnum):
    # Personal context
    CORE_FACTS = "CoreFacts"
    CAREER = "Career"
    GOALS = "Goals"
    MAJOR_PREFERENCES = "MajorPreferences"
    IMPORTANT_RELATIONSHIPS = "ImportantRelationships"
    TECHNOLOGIES = "Technologies"
    PROJECTS = "Projects"
    # Agent / system context
    AGENT_OBSERVATION = "AgentObservation"
    TOOL_RESULT = "ToolResult"
    SYSTEM_EVENT = "SystemEvent"
    INSTRUCTION = "Instruction"
    FINE_TUNE_CANDIDATE = "FineTuneCandidate"
    # Fallback
    GENERAL = "General"


class SourceType(StrEnum):
    """Origin of the memory — critical for filtering and fine-tune dataset curation."""

    CHAT = "chat"
    AGENT_EVENT = "agent_event"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    MANUAL = "manual"
    API_INGEST = "api_ingest"


class ImportanceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Core Memory Model ─────────────────────────────────────────────────────────


class Memory(BaseModel):
    """
    A single structured memory unit.

    Designed to be:
      - Pluggable: any agent/source can produce memories via source_type + agent_id
      - Traceable: source_text preserves the original context for fine-tuning
      - Groupable: session_id links memories from the same run/conversation
      - Self-improving: access_count + last_accessed_at enable relevance weighting
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    agent_id: str | None = Field(default=None, description="Originating agent identifier")
    session_id: str | None = Field(
        default=None, description="Groups memories from the same session/run"
    )
    category: MemoryCategory = MemoryCategory.GENERAL
    source_type: SourceType = SourceType.CHAT
    content: str = Field(description="Distilled, self-contained fact")
    source_text: str | None = Field(
        default=None, description="Raw original text this memory was extracted from"
    )
    importance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tags: list[str] = Field(
        default_factory=list, description="Free-form keyword tags for fast filtering"
    )
    access_count: int = Field(
        default=0, description="Number of times this memory has been retrieved"
    )
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
    )


# ── Extracted / Candidate Memory (before persistence) ────────────────────────


class ExtractedMemory(BaseModel):
    """Raw memory candidate produced by the extractor before scoring/embedding."""

    category: MemoryCategory
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_text: str | None = None
    tags: list[str] = Field(default_factory=list)


# ── Ingest Request Models ─────────────────────────────────────────────────────


class RawIngestRequest(BaseModel):
    """Push any raw text to be extracted and stored as memories."""

    user_id: str
    text: str = Field(..., min_length=1, description="Raw text to extract memories from")
    agent_id: str | None = None
    session_id: str | None = None
    source_type: SourceType = SourceType.API_INGEST
    tags: list[str] = Field(default_factory=list)


class AgentEventRequest(BaseModel):
    """Push a structured agent event (tool call, observation, etc.)."""

    user_id: str
    agent_id: str
    session_id: str | None = None
    event_type: Literal["tool_call", "observation", "reflection", "instruction"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.8, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class DirectMemoryRequest(BaseModel):
    """Directly insert pre-formed memories — no LLM extraction."""

    user_id: str
    agent_id: str | None = None
    session_id: str | None = None
    category: MemoryCategory = MemoryCategory.GENERAL
    source_type: SourceType = SourceType.MANUAL
    content: str
    importance: float = Field(ge=0.6, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Search / Retrieval ────────────────────────────────────────────────────────


class MemorySearchResult(BaseModel):
    memory: Memory
    similarity: float = Field(ge=0.0, le=1.0)


# ── Fine-tune Dataset ─────────────────────────────────────────────────────────


class FineTuneMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class FineTuneRecord(BaseModel):
    """Single record in an OpenAI-compatible fine-tuning dataset."""

    messages: list[FineTuneMessage]
    metadata: dict[str, Any] = Field(default_factory=dict)
