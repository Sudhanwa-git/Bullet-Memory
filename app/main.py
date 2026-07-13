"""
Application entry point.

Initialises the FastAPI app, mounts routers, and configures startup / shutdown hooks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.router import router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Startup and shutdown lifecycle manager."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("bullet_memory.startup", host=settings.API_HOST, port=settings.API_PORT)

    os.makedirs("data", exist_ok=True)
    # Eagerly initialise the DB so tables exist before the first request
    from app.adapters.database import DatabaseAdapter

    db = DatabaseAdapter()
    await db.initialise()
    logger.info("bullet_memory.db.ready")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("bullet_memory.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bullet Memory",
        description="Semantic memory engine for LLM agents — powered by local Ollama models",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
