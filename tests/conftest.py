"""
Shared pytest fixtures.
"""
from __future__ import annotations

import pytest

from app.adapters.vector import InMemoryVectorStore
from app.memory.models import Memory, MemoryCategory


@pytest.fixture()
def sample_memory() -> Memory:
    return Memory(
        user_id="test_user",
        category=MemoryCategory.SKILLS,
        content="Experienced with Python and FastAPI",
        importance=0.9,
        confidence=0.95,
    )


@pytest.fixture()
def in_memory_vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()
