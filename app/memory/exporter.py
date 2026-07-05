"""
Fine-tune Dataset Exporter.

Converts stored memories into structured datasets ready for:
  - OpenAI fine-tuning (chat format JSONL)
  - Generic JSONL export
  - HuggingFace-compatible instruction format

Usage:
    exporter = FineTuneExporter(db)
    records = await exporter.export(user_id="u1", format="openai", min_importance=0.7)
    await exporter.write_jsonl(records, path="./dataset.jsonl")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import structlog

from app.adapters.database import DatabaseAdapter
from app.memory.models import FineTuneMessage, FineTuneRecord, Memory, MemoryCategory, SourceType

logger = structlog.get_logger(__name__)

ExportFormat = Literal["openai", "jsonl", "instruction"]


class FineTuneExporter:
    """
    Exports memory records as structured datasets for model fine-tuning.
    """

    def __init__(self, db: DatabaseAdapter) -> None:
        self._db = db

    async def export(
        self,
        user_id: str,
        format: ExportFormat = "openai",
        min_importance: float = 0.6,
        categories: list[MemoryCategory] | None = None,
        source_types: list[SourceType] | None = None,
        session_id: str | None = None,
    ) -> list[FineTuneRecord]:
        """
        Fetch memories and convert them to fine-tuning records.
        Returns a list of FineTuneRecord objects.
        """
        memories = await self._db.list_memories(
            user_id=user_id,
            session_id=session_id,
            min_importance=min_importance,
        )

        # Apply optional filters
        if categories:
            cat_values = {c.value for c in categories}
            memories = [m for m in memories if m.category.value in cat_values]
        if source_types:
            st_values = {s.value for s in source_types}
            memories = [m for m in memories if m.source_type.value in st_values]

        logger.info("exporter.export.start", user_id=user_id, total=len(memories), format=format)

        if format == "openai":
            return [self._to_openai_record(m) for m in memories]
        elif format == "instruction":
            return [self._to_instruction_record(m) for m in memories]
        else:
            return [self._to_raw_record(m) for m in memories]

    def to_jsonl_string(self, records: list[FineTuneRecord]) -> str:
        """Serialize records to JSONL string."""
        lines = [json.dumps(r.model_dump(), ensure_ascii=False) for r in records]
        return "\n".join(lines)

    async def write_jsonl(self, records: list[FineTuneRecord], path: str) -> int:
        """Write records to a JSONL file. Returns number of records written."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
        logger.info("exporter.write_jsonl.done", path=str(p), records=len(records))
        return len(records)

    # ── Format Converters ─────────────────────────────────────────────────────

    @staticmethod
    def _to_openai_record(memory: Memory) -> FineTuneRecord:
        """
        Converts a memory to OpenAI chat fine-tuning format:
        {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
        """
        system_msg = FineTuneMessage(
            role="system",
            content=(
                "You are a highly personalized AI assistant with persistent memory. "
                "Use this context to provide tailored, context-aware responses."
            ),
        )

        if memory.source_text:
            user_content = memory.source_text
        else:
            user_content = f"What do you know about my {memory.category.value.lower()}?"

        assistant_content = memory.content

        return FineTuneRecord(
            messages=[
                system_msg,
                FineTuneMessage(role="user", content=user_content),
                FineTuneMessage(role="assistant", content=assistant_content),
            ],
            metadata={
                "memory_id": memory.id,
                "category": memory.category.value,
                "source_type": memory.source_type.value,
                "importance": memory.importance,
                "confidence": memory.confidence,
                "tags": memory.tags,
            },
        )

    @staticmethod
    def _to_instruction_record(memory: Memory) -> FineTuneRecord:
        """HuggingFace instruction-following format."""
        instruction = f"Extract and summarize the key fact about [{memory.category.value}]."
        input_text = memory.source_text or ""
        output_text = memory.content

        return FineTuneRecord(
            messages=[
                FineTuneMessage(
                    role="user",
                    content=f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:",
                ),
                FineTuneMessage(role="assistant", content=output_text),
            ],
            metadata={"memory_id": memory.id, "category": memory.category.value},
        )

    @staticmethod
    def _to_raw_record(memory: Memory) -> FineTuneRecord:
        """Plain JSONL with all memory fields."""
        return FineTuneRecord(
            messages=[FineTuneMessage(role="assistant", content=memory.content)],
            metadata={
                "memory_id": memory.id,
                "user_id": memory.user_id,
                "agent_id": memory.agent_id,
                "session_id": memory.session_id,
                "category": memory.category.value,
                "source_type": memory.source_type.value,
                "importance": memory.importance,
                "confidence": memory.confidence,
                "tags": memory.tags,
                "source_text": memory.source_text,
                "access_count": memory.access_count,
                "created_at": memory.created_at.isoformat(),
            },
        )
