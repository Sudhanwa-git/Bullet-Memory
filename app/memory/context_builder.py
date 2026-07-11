"""
Context Builder Engine — Optimal prompt construction.

This module is responsible for ranking, filtering, and compressing retrieved
memories to maximize information density while adhering to token limits.
"""

from __future__ import annotations

import structlog

from app.memory.models import Memory

logger = structlog.get_logger(__name__)


class ContextBuilder:
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough heuristic for token estimation (approx 4 chars per token).
        In production, we would use tiktoken or the model's specific tokenizer.
        """
        return len(text) // 4

    def build_context(self, query: str, memories: list[Memory]) -> list[Memory]:
        """
        Given a list of retrieved memories, builds the optimal context window.
        
        It ranks memories by importance, semantic relevance (if available), 
        and packs them into the token budget using a greedy approach.
        """
        if not memories:
            return []

        # We assume memories are already scored/ranked by the Retriever.
        # Here we just apply the token density filter to prevent prompt bloat.
        
        packed_memories: list[Memory] = []
        current_tokens = 0
        
        for mem in memories:
            mem_tokens = self._estimate_tokens(mem.content)
            
            # If a single memory is too large, we might skip it or ideally chunk it.
            # For now, we strictly pack until we hit the budget.
            if current_tokens + mem_tokens > self.max_tokens:
                logger.debug("context_builder.budget_exceeded", 
                             memory_id=mem.id, 
                             mem_tokens=mem_tokens, 
                             current_tokens=current_tokens)
                continue
                
            packed_memories.append(mem)
            current_tokens += mem_tokens

        logger.info(
            "context_builder.build_context.done",
            input_memories=len(memories),
            packed_memories=len(packed_memories),
            total_tokens=current_tokens,
            max_tokens=self.max_tokens
        )
        return packed_memories
