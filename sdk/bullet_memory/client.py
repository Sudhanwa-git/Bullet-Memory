"""
Bullet Memory Python SDK

A lightweight, async-first client for the Bullet Memory engine.
Plug this into any agent, pipeline, or system to enable persistent memory.

Quick start:
    from bullet_memory import BulletMemoryClient

    client = BulletMemoryClient(base_url="http://localhost:8000")

    # Feed raw text for extraction
    await client.ingest_raw("I primarily use Python and FastAPI for backend work.", user_id="agent-1")

    # Retrieve context before generating a response
    context = await client.retrieve("What tech stack does the user prefer?", user_id="agent-1")

    # Export fine-tuning dataset
    dataset = await client.export_finetune(user_id="agent-1")
"""
from __future__ import annotations

import json
from typing import Any, Literal

import httpx

ExportFormat = Literal["openai", "instruction", "jsonl"]
SourceType = Literal["chat", "agent_event", "tool_call", "observation", "manual", "api_ingest"]


class BulletMemoryClient:
    """
    Async HTTP client for the Bullet Memory engine.

    All methods are async and should be awaited.
    The client manages a shared httpx.AsyncClient — call .close() when done,
    or use as an async context manager.

    Example:
        async with BulletMemoryClient("http://localhost:8000") as client:
            await client.ingest_raw("I love Python.", user_id="u1")
            ctx = await client.retrieve("favorite language?", user_id="u1")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=headers,
        )

    async def __aenter__(self) -> "BulletMemoryClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest_raw(
        self,
        text: str,
        user_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: SourceType = "api_ingest",
        tags: list[str] | None = None,
        sync: bool = True,
    ) -> dict[str, Any]:
        """
        Ingest raw text and extract durable memories from it.

        Args:
            text:        Any text string — conversation, document, agent output.
            user_id:     The user or entity the memories belong to.
            agent_id:    Optional agent identifier (for multi-agent tracking).
            session_id:  Optional session tag to group related memories.
            source_type: Origin of the text.
            tags:        Free-form keyword tags.
            sync:        If True, waits for extraction. If False, fires-and-forgets.

        Returns:
            dict with status and memories_stored count (if sync=True).
        """
        endpoint = "/ingest/raw/sync" if sync else "/ingest/raw"
        payload = {
            "user_id": user_id,
            "text": text,
            "source_type": source_type,
            "tags": tags or [],
        }
        if agent_id:
            payload["agent_id"] = agent_id
        if session_id:
            payload["session_id"] = session_id

        resp = await self._client.post(endpoint, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def ingest_event(
        self,
        content: str,
        user_id: str,
        agent_id: str,
        event_type: Literal["tool_call", "observation", "reflection", "instruction"] = "observation",
        session_id: str | None = None,
        importance: float = 0.8,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Push a structured agent event directly.
        No LLM extraction — the content IS the memory.

        Best for: tool call results, agent observations, system events.
        """
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "content": content,
            "importance": importance,
            "tags": tags or [],
            "metadata": metadata or {},
        }
        if session_id:
            payload["session_id"] = session_id

        resp = await self._client.post("/ingest/event", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def store(
        self,
        content: str,
        user_id: str,
        importance: float,
        category: str = "General",
        source_type: SourceType = "manual",
        agent_id: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Directly insert a pre-formed memory with full control.
        No LLM extraction. Caller sets all fields.
        """
        payload = {
            "user_id": user_id,
            "category": category,
            "source_type": source_type,
            "content": content,
            "importance": importance,
            "tags": tags or [],
            "metadata": metadata or {},
        }
        if agent_id:
            payload["agent_id"] = agent_id
        if session_id:
            payload["session_id"] = session_id

        resp = await self._client.post("/ingest/direct", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ── Retrieval ─────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Semantically retrieve memories relevant to a query.
        Returns a list of memory objects ordered by relevance.

        Usage:
            context = await client.retrieve("What languages does the user know?", user_id="u1")
            prompt = build_prompt(context)
        """
        resp = await self._client.post(
            "/memories/search",
            json={"user_id": user_id, "query": query, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json().get("memories", [])

    async def get_context_string(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> str:
        """
        Retrieve relevant memories and format them as a context string
        ready to inject into an LLM prompt.

        Returns:
            Formatted string like:
            "- [Career] User is a senior Python engineer
             - [Goals] User wants to build AI products"
        """
        memories = await self.retrieve(query=query, user_id=user_id, top_k=top_k)
        if not memories:
            return ""
        lines = [f"- [{m['category']}] {m['content']}" for m in memories]
        return "\n".join(lines)

    async def list_all(
        self,
        user_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: str | None = None,
        category: str | None = None,
        min_importance: float = 0.0,
    ) -> list[dict[str, Any]]:
        """List all stored memories with optional filters."""
        params: dict[str, Any] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if session_id:
            params["session_id"] = session_id
        if source_type:
            params["source_type"] = source_type
        if category:
            params["category"] = category
        if min_importance > 0.0:
            params["min_importance"] = min_importance

        resp = await self._client.get(f"/memories/{user_id}", params=params)
        resp.raise_for_status()
        return resp.json().get("memories", [])

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        resp = await self._client.delete(f"/memories/{memory_id}")
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    # ── Export ────────────────────────────────────────────────────────────────

    async def export_finetune(
        self,
        user_id: str,
        format: ExportFormat = "openai",
        min_importance: float = 0.6,
        session_id: str | None = None,
    ) -> str:
        """
        Export memories as a JSONL fine-tuning dataset.

        Args:
            format:         "openai" | "instruction" | "jsonl"
            min_importance: Only export memories above this threshold.
            session_id:     Filter to a specific session's memories.

        Returns:
            JSONL string ready to write to a file or feed to a fine-tuning pipeline.

        Example:
            dataset = await client.export_finetune(user_id="u1", format="openai")
            with open("finetune.jsonl", "w") as f:
                f.write(dataset)
        """
        params: dict[str, Any] = {"format": format, "min_importance": min_importance}
        if session_id:
            params["session_id"] = session_id

        resp = await self._client.get(f"/memories/export/{user_id}", params=params)
        resp.raise_for_status()
        return resp.text

    # ── Health ────────────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Check if the Bullet Memory engine is running."""
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()
