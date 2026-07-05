"""
LLM Adapter — provider-agnostic interface for language model calls.

Add new providers by implementing LLMAdapter and registering in get_llm_adapter().
Supported providers: openai | ollama
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ── Abstract interface ────────────────────────────────────────────────────────


class LLMAdapter(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant text."""

    @abstractmethod
    async def stream_chat(self, system: str, user: str):
        """Yield tokens asynchronously as they are generated."""


# ── OpenAI Implementation ─────────────────────────────────────────────────────


class OpenAIAdapter(LLMAdapter):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    async def stream_chat(self, system: str, user: str):
        # OpenAI Streaming fallback (not currently used)
        raise NotImplementedError("Streaming not yet implemented for OpenAI")


# ── Ollama Implementation ─────────────────────────────────────────────────────


class OllamaAdapter(LLMAdapter):
    """
    Calls a locally running Ollama server via its REST API.
    Uses /api/chat for multi-turn chat completions.
    """

    def __init__(self) -> None:
        import httpx

        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.LLM_MODEL
        self._client = httpx.AsyncClient(timeout=120.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "keep_alive": "1h",
            "options": {
                "temperature": 0.3,
                "num_predict": 512,
                "num_ctx": 2048,
            },
        }

        # If the system prompt requests JSON output, enable Ollama's JSON mode
        if "json" in system.lower() or "JSON" in system:
            payload["format"] = "json"

        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        logger.debug(
            "ollama.complete.done",
            model=self._model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )
        return content

    async def stream_chat(self, system: str, user: str):
        import json

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
            "keep_alive": "1h",
            "options": {
                "temperature": 0.3,
                "num_predict": 512,
                "num_ctx": 2048,
            },
        }

        async with self._client.stream(
            "POST", f"{self._base_url}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content")
                    if chunk:
                        yield chunk
                except json.JSONDecodeError:
                    pass


# ── Factory ───────────────────────────────────────────────────────────────────


def get_llm_adapter() -> LLMAdapter:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIAdapter()
    if provider == "ollama":
        return OllamaAdapter()
    raise ValueError(f"Unsupported LLM provider: {provider!r}. Supported: openai | ollama")
