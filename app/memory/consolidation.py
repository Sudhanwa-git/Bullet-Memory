"""
Memory Consolidation Background Task.

Responsible for periodically scanning old memories to detect duplicates,
resolve contradictions, and synthesize them into higher-level insights.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.adapters.database import DatabaseAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.vector import VectorStoreAdapter
from app.memory.embeddings import EmbeddingGenerator
from app.memory.models import DirectMemoryRequest, MemoryCategory, SourceType
from app.memory.service import MemoryService

logger = structlog.get_logger(__name__)


class SynthesizedFacts(BaseModel):
    facts: list[str] = Field(description="List of consolidated, synthesized facts.")
    archived_topics: list[str] = Field(description="Topics that were merged.")


CONSOLIDATION_PROMPT = """
You are a Memory Consolidation Engine.
Your task is to review a list of fragmented, potentially duplicate, or contradictory memories for a specific category.
You must synthesize them into a clean, concise, and deduplicated list of core facts.
If there are contradictions, assume the later facts (closer to the bottom of the list) are more recent and override the older ones.
Do not lose any unique information, but remove redundancy.

Respond in JSON matching this schema:
{{
  "facts": ["Fact 1", "Fact 2"],
  "archived_topics": ["Topic 1", "Topic 2"]
}}

Memories to consolidate:
{memory_text}
"""


class MemoryConsolidator:
    def __init__(
        self,
        memory_service: MemoryService,
        db: DatabaseAdapter,
        llm: LLMAdapter,
    ) -> None:
        self._memory = memory_service
        self._db = db
        self._llm = llm

    async def run_consolidation_cycle(self, user_id: str) -> dict[str, Any]:
        """Scans memories and synthesizes them by category."""
        logger.info("memory_consolidation.started", user_id=user_id)
        
        # We will consolidate PREFERENCES and GOALS
        categories_to_consolidate = [MemoryCategory.MAJOR_PREFERENCES, MemoryCategory.GOALS, MemoryCategory.CORE_FACTS]
        
        stats = {"deleted": 0, "synthesized": 0}
        
        for cat in categories_to_consolidate:
            # Fetch all memories in this category
            memories = await self._memory.get_all(user_id=user_id, category=cat)
            if len(memories) < 3:
                continue # Not enough to bother consolidating
                
            # Order them chronologically (get_all returns descending by default, so we reverse it)
            memories = sorted(memories, key=lambda m: m.created_at)
            
            memory_text = "\n".join(f"- {m.content}" for m in memories)
            prompt = CONSOLIDATION_PROMPT.format(memory_text=memory_text)
            
            try:
                result_json = await self._llm.complete_json(
                    system="You are an expert memory synthesis engine.",
                    user=prompt,
                    schema=SynthesizedFacts.model_json_schema()
                )
                
                result = SynthesizedFacts.model_validate_json(result_json)
                
                if not result.facts:
                    continue
                    
                # 1. Delete old memories
                for m in memories:
                    await self._memory.delete(m.id)
                    stats["deleted"] += 1
                    
                # 2. Insert new synthesized memories
                for fact in result.facts:
                    req = DirectMemoryRequest(
                        user_id=user_id,
                        category=cat,
                        source_type=SourceType.SYSTEM_EVENT,
                        content=fact,
                        importance=0.9,
                        confidence=1.0,
                        tags=result.archived_topics
                    )
                    await self._memory.store_direct(req)
                    stats["synthesized"] += 1
                    
            except Exception as e:
                logger.error("memory_consolidation.error", category=cat.value, error=str(e))
                
        logger.info("memory_consolidation.completed", user_id=user_id, stats=stats)
        return stats


