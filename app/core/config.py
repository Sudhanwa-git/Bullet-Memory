"""
Centralised application configuration.

All values are read from environment variables (or a .env file).
Changing provider or threshold behaviour requires only .env edits.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM ──────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = Field(default="ollama", description="openai | ollama")
    LLM_MODEL: str = Field(default="qwen2.5-coder:7b")
    OPENAI_API_KEY: str = Field(default="")

    # ── Ollama ───────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Base URL for local Ollama server"
    )

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = Field(default="ollama", description="openai | ollama")
    EMBEDDING_MODEL: str = Field(default="nomic-embed-text")
    EMBEDDING_DIMENSIONS: int = Field(
        default=768
    )  # nomic-embed-text=768, text-embedding-3-small=1536

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./bullet_memory.db")

    # ── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_STORE_PROVIDER: str = Field(default="chroma", description="chroma | in_memory")
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_db")
    # When set, connects to a remote ChromaDB HTTP server (e.g. in Docker)
    CHROMA_HOST: str = Field(default="")
    CHROMA_PORT: int = Field(default=8000)

    # ── Memory tuning ─────────────────────────────────────────────────────────
    IMPORTANCE_THRESHOLD: float = Field(default=0.4, ge=0.0, le=1.0)
    SIMILARITY_THRESHOLD: float = Field(default=0.75, ge=0.0, le=1.0)
    TOP_K_RETRIEVAL: int = Field(default=5, ge=1)

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO")

    # ── API ───────────────────────────────────────────────────────────────────
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)


settings = Settings()
