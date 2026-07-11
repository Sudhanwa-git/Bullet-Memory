"""
Dependency injection helpers for FastAPI.

All adapters and services are created once per application startup
and reused across requests via FastAPI's dependency system.
"""

from __future__ import annotations

from functools import lru_cache

from app.adapters.database import DatabaseAdapter
from app.adapters.embedding import get_embedding_adapter
from app.adapters.llm import get_llm_adapter
from app.adapters.vector import get_vector_store
from app.core.orchestrator import MemoryOrchestrator
from app.memory.embeddings import EmbeddingGenerator
from app.memory.extractor import MemoryExtractor
from app.memory.retriever import MemoryRetriever
from app.memory.scorer import ImportanceScorer
from app.memory.service import MemoryService
from app.memory.updater import MemoryUpdater
from app.memory.working_memory import WorkingMemoryEngine


@lru_cache(maxsize=1)
def _build_services() -> tuple[MemoryService, MemoryOrchestrator]:
    """
    Build the service graph once.
    lru_cache ensures we create only one instance of each expensive resource.
    """
    llm = get_llm_adapter()
    embedding_adapter = get_embedding_adapter()
    db = DatabaseAdapter()
    vector_store = get_vector_store()

    embedder = EmbeddingGenerator(embedding_adapter)
    extractor = MemoryExtractor(llm)
    scorer = ImportanceScorer()
    retriever = MemoryRetriever(vector_store, embedder, db)
    updater = MemoryUpdater(db, vector_store, embedder)

    memory_service = MemoryService(
        extractor=extractor,
        scorer=scorer,
        embedder=embedder,
        retriever=retriever,
        updater=updater,
        db=db,
        vector_store=vector_store,
    )

    from app.memory.cache import SemanticCache
    semantic_cache = SemanticCache(embedder)

    orchestrator = MemoryOrchestrator(memory_service=memory_service, llm=llm, cache=semantic_cache)
    return memory_service, orchestrator


@lru_cache(maxsize=1)
def _build_working_memory_engine() -> WorkingMemoryEngine:
    """Build and initialise the WorkingMemoryEngine once per process."""
    return WorkingMemoryEngine()


def get_memory_service() -> MemoryService:
    service, _ = _build_services()
    return service


def get_orchestrator() -> MemoryOrchestrator:
    _, orchestrator = _build_services()
    return orchestrator


def get_working_memory_engine() -> WorkingMemoryEngine:
    return _build_working_memory_engine()
