"""
Memory Orchestrator — central coordinator for every chat request.

Retrieval  →  Prompt Build  →  LLM Call  →  Memory Pipeline  →  Response
"""

from __future__ import annotations

import time

import structlog

from app.adapters.llm import LLMAdapter
from app.core.config import settings
from app.core.prompts import DEFAULT_SYSTEM_PROMPT, MEMORY_CONTEXT_HEADER
from app.memory.cache import SemanticCache
from app.memory.context_builder import ContextBuilder
from app.memory.service import MemoryService

logger = structlog.get_logger(__name__)


class MemoryOrchestrator:
    """
    Coordinates retrieval, prompt construction, LLM calls, and memory storage.
    Business logic lives in MemoryService and adapters — this class only orchestrates.
    """

    def __init__(
        self, memory_service: MemoryService, llm: LLMAdapter, cache: SemanticCache | None = None
    ) -> None:
        self._memory = memory_service
        self._llm = llm
        self._cache = cache
        self._context_builder = ContextBuilder(max_tokens=2000)

    async def chat(
        self,
        user_id: str,
        message: str,
        system_prompt: str | None = None,
    ) -> dict:
        """
        Full request lifecycle:
        1. Retrieve relevant memories
        2. Build enriched prompt
        3. Call LLM
        4. Extract and persist new memories
        5. Return response
        """
        t0 = time.perf_counter()
        log = logger.bind(user_id=user_id)

        if self._cache:
            cached_response = await self._cache.get(user_id, message)
            if cached_response:
                cached_response["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                log.info("orchestrator.chat.cache_hit", latency_ms=cached_response["latency_ms"])
                return cached_response

        # ── 1. Retrieve ───────────────────────────────────────────────────────
        log.info("orchestrator.retrieve.start")
        t_ret = time.perf_counter()
        memories = await self._memory.retrieve(
            user_id=user_id,
            query=message,
            top_k=settings.TOP_K_RETRIEVAL,
            threshold=settings.SIMILARITY_THRESHOLD,
        )
        log.info(
            "orchestrator.retrieve.done",
            count=len(memories),
            latency_ms=round((time.perf_counter() - t_ret) * 1000, 2),
        )

        # ── 1.5 Filter and build dense context ────────────────────────────────
        log.info("orchestrator.context_builder.start")
        t_ctx = time.perf_counter()
        memories = self._context_builder.build_context(message, memories)
        log.info(
            "orchestrator.context_builder.done",
            latency_ms=round((time.perf_counter() - t_ctx) * 1000, 2),
        )

        # ── 2. Build prompt ───────────────────────────────────────────────────
        system = self._build_system_prompt(system_prompt or DEFAULT_SYSTEM_PROMPT, memories)

        # ── 3. LLM inference ──────────────────────────────────────────────────
        log.info("orchestrator.llm.start", model=settings.LLM_MODEL)
        t_llm = time.perf_counter()
        response_text = await self._llm.complete(system=system, user=message)
        log.info(
            "orchestrator.llm.done",
            latency_ms=round((time.perf_counter() - t_llm) * 1000, 2),
        )

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        log.info("orchestrator.chat.done", total_latency_ms=total_ms)

        retrieved_context = [{"category": m.category, "content": m.content} for m in memories]

        payload = {
            "response": response_text,
            "memories_retrieved": len(memories),
            "retrieved_context": retrieved_context,
            "latency_ms": total_ms,
        }

        if self._cache:
            await self._cache.set(user_id, message, payload)

        return payload

    async def process_memory_background(
        self, user_id: str, message: str, response_text: str
    ) -> None:
        """
        Background task: Extract and persist new memories from the conversation.
        """
        log = logger.bind(user_id=user_id)
        log.info("orchestrator.memory_pipeline.start")
        try:
            stored = await self._memory.process_conversation(
                user_id=user_id,
                user_message=message,
                assistant_response=response_text,
            )
            log.info("orchestrator.memory_pipeline.done", stored=stored)
        except Exception as e:
            log.error("orchestrator.memory_pipeline.error", error=str(e))

    async def chat_stream(
        self, user_id: str, message: str, system_prompt: str | None = None, background_tasks=None
    ):
        """
        Streaming chat lifecycle:
        1. Retrieve memories
        2. Yield the retrieved context immediately
        3. Stream LLM tokens
        4. Schedule background extraction when complete
        """
        import orjson

        t0 = time.perf_counter()
        log = logger.bind(user_id=user_id)

        if self._cache:
            cached_response = await self._cache.get(user_id, message)
            if cached_response:
                log.info("orchestrator.chat_stream.cache_hit")
                yield f"data: {orjson.dumps({'type': 'context', 'data': cached_response.get('retrieved_context', [])}).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'token', 'data': cached_response.get('response', '')}).decode('utf-8')}\n\n"
                return

        log.info("orchestrator.retrieve_stream.start")
        memories = await self._memory.retrieve(
            user_id=user_id,
            query=message,
            top_k=settings.TOP_K_RETRIEVAL,
            threshold=settings.SIMILARITY_THRESHOLD,
        )

        memories = self._context_builder.build_context(message, memories)

        # Yield the retrieved context as the first SSE chunk
        retrieved_context = [{"category": m.category, "content": m.content} for m in memories]
        yield f"data: {orjson.dumps({'type': 'context', 'data': retrieved_context}).decode('utf-8')}\n\n"

        system = self._build_system_prompt(system_prompt or DEFAULT_SYSTEM_PROMPT, memories)

        log.info("orchestrator.llm_stream.start", model=settings.LLM_MODEL)

        full_response = []
        async for chunk in self._llm.stream_chat(system=system, user=message):
            full_response.append(chunk)
            yield f"data: {orjson.dumps({'type': 'token', 'data': chunk}).decode('utf-8')}\n\n"

        final_text = "".join(full_response)

        if self._cache:
            payload = {
                "response": final_text,
                "memories_retrieved": len(memories),
                "retrieved_context": retrieved_context,
            }
            await self._cache.set(user_id, message, payload)

        if background_tasks:
            background_tasks.add_task(
                self.process_memory_background,
                user_id=user_id,
                message=message,
                response_text=final_text,
            )

        log.info(
            "orchestrator.chat_stream.done",
            total_latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_system_prompt(base: str, memories: list) -> str:
        if not memories:
            return base
        mem_block = "\n".join(f"- [{m.category}] {m.content}" for m in memories)
        return MEMORY_CONTEXT_HEADER.format(memories=mem_block) + base
