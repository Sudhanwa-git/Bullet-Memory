"""
Main API router — mounts all sub-routers and the health check.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import chat, ingest, memory
from app.core.config import settings

router = APIRouter()

# ── Sub-routers ───────────────────────────────────────────────────────────────
router.include_router(chat.router)
router.include_router(memory.router)
router.include_router(ingest.router)


# ── Health check ──────────────────────────────────────────────────────────────
@router.get("/health", tags=["meta"], summary="Health check")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "vector_store": settings.VECTOR_STORE_PROVIDER,
    }


@router.get("/config", tags=["meta"], summary="Active configuration (non-sensitive)")
async def config() -> dict:
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "importance_threshold": settings.IMPORTANCE_THRESHOLD,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "top_k_retrieval": settings.TOP_K_RETRIEVAL,
    }
