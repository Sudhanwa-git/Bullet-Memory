"""
Embedding Adapter — provider-agnostic interface for generating vector embeddings.

Swap providers by implementing EmbeddingAdapter and updating get_embedding_adapter().
Supported providers: openai | ollama
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger(__name__)


# ── Abstract interface ────────────────────────────────────────────────────────


class EmbeddingAdapter(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single string and return the float vector."""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings and return a list of float vectors."""


# ── OpenAI Implementation ─────────────────────────────────────────────────────


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


# ── Ollama Embedding Implementation ───────────────────────────────────────────────


class OllamaEmbeddingAdapter(EmbeddingAdapter):
    """
    Generates embeddings using a locally running Ollama model.
    Defaults to nomic-embed-text which produces 768-dimensional vectors.
    """

    def __init__(self) -> None:
        import httpx

        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.EMBEDDING_MODEL
        self._client = httpx.AsyncClient(timeout=60.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Ollama doesn't support batch embeddings natively — use asyncio.gather for concurrency."""
        import asyncio

        return list(await asyncio.gather(*(self.embed(t) for t in texts)))


# ── Factory ───────────────────────────────────────────────────────────────────


def get_embedding_adapter() -> EmbeddingAdapter:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        return OpenAIEmbeddingAdapter()
    if provider == "ollama":
        return OllamaEmbeddingAdapter()
    raise ValueError(f"Unsupported embedding provider: {provider!r}. Supported: openai | ollama")
