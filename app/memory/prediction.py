"""
Prediction Engine — Proactive memory pre-fetching daemon.

The Prediction Engine solves the single biggest latency source in memory-augmented
agents: waiting for vector retrieval AFTER the user/agent sends a message.

Instead of being reactive, this engine monitors the agent's Working Memory state
and continuously pre-warms the SemanticCache with memories it predicts will be
needed soon.

When the orchestrator then calls retrieve(), the SemanticCache already has the
answer and returns it in ~1ms instead of ~200ms+ for a full vector search.

Strategy:
  - On every Working Memory update, extract key terms from the goal + pending steps
  - Pre-fetch the top-k most semantically relevant memories for those terms
  - Store results in the SemanticCache so future retrieve() calls are instant
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from app.memory.retriever import MemoryRetriever

if TYPE_CHECKING:
    from app.memory.cache import SemanticCache
    from app.memory.working_memory import WorkingMemoryState

logger = structlog.get_logger(__name__)


class PredictionEngine:
    """
    Background daemon that proactively pre-fetches memories based on
    current Working Memory state.

    This dramatically reduces perceived retrieval latency from ~200ms+ to ~1ms
    for cache hits, by predicting what information the agent will need before
    it explicitly asks.

    Usage:
        engine = PredictionEngine(retriever, cache)

        # Call this whenever Working Memory is updated — it runs non-blocking
        asyncio.create_task(engine.prefetch(state))
    """

    def __init__(self, retriever: MemoryRetriever, cache: SemanticCache) -> None:
        self._retriever = retriever
        self._cache = cache

    async def prefetch(self, state: WorkingMemoryState) -> None:
        """
        Analyze current working memory and pre-warm the cache for likely queries.

        Constructs synthetic "predictive queries" from the agent's goal and
        upcoming steps, then fetches and caches relevant memories.
        """
        predictive_queries = self._build_predictive_queries(state)

        if not predictive_queries:
            return

        logger.debug(
            "prediction_engine.prefetch.start",
            session_id=state.session_id,
            num_queries=len(predictive_queries),
        )

        tasks = [
            self._prefetch_single(state.user_id, query)
            for query in predictive_queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(
            "prediction_engine.prefetch.done",
            session_id=state.session_id,
            successful=successful,
            total=len(tasks),
        )

    async def _prefetch_single(self, user_id: str, query: str) -> None:
        """Pre-fetch memories for a single predictive query and warm the cache."""
        try:
            # Check cache first to avoid redundant vector searches
            cached = await self._cache.get(user_id, query)
            if cached is not None:
                logger.debug("prediction_engine.cache_already_warm", query=query[:50])
                return

            # Run vector retrieval
            memories = await self._retriever.retrieve(
                user_id=user_id,
                query=query,
                top_k=5,
            )

            if memories:
                # Store in cache so the orchestrator gets instant hits
                retrieved_context = [
                    {"category": str(m.category), "content": m.content}
                    for m in memories
                ]
                payload = {
                    "response": "",  # Prefetch only caches context, not LLM responses
                    "memories_retrieved": len(memories),
                    "retrieved_context": retrieved_context,
                    "prefetched": True,
                }
                await self._cache.set(user_id, query, payload)
                logger.debug(
                    "prediction_engine.prefetched",
                    query=query[:50],
                    memories=len(memories),
                )
        except Exception as e:
            logger.error("prediction_engine.prefetch_error", query=query[:50], error=str(e))

    @staticmethod
    def _build_predictive_queries(state: WorkingMemoryState) -> list[str]:
        """
        Build synthetic queries from working memory state.

        Looks at: goal, next pending step, and recent variables.
        Returns deduplicated list of queries to pre-fetch.
        """
        queries: list[str] = []

        # Primary: the agent's goal
        if state.goal:
            queries.append(state.goal)

        # Secondary: the next pending step (most immediate context)
        if state.pending_steps:
            next_step = state.pending_steps[0]
            queries.append(next_step)
            # Also combine with goal for richer context
            if state.goal:
                queries.append(f"{state.goal}: {next_step}")

        # Tertiary: recent scratchpad reasoning
        if state.scratchpad and len(state.scratchpad) > 20:
            # Take the last meaningful snippet of scratchpad
            snippet = state.scratchpad[-200:].strip()
            if snippet:
                queries.append(snippet)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for q in queries:
            if q not in seen and q.strip():
                seen.add(q)
                unique.append(q)

        return unique
