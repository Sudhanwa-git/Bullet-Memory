"""
Tests for InMemoryVectorStore — pure cosine similarity search.
"""
from __future__ import annotations

import math

import pytest

from app.adapters.vector import InMemoryVectorStore
from app.memory.models import Memory, MemoryCategory


def _unit_vec(dims: int, hot: int) -> list[float]:
    v = [0.0] * dims
    v[hot] = 1.0
    return v


@pytest.fixture()
def store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture()
def memory_a() -> Memory:
    return Memory(
        user_id="alice",
        category=MemoryCategory.SKILLS,
        content="Expert in Python",
        importance=0.9,
        confidence=0.95,
        embedding=_unit_vec(4, 0),
    )


@pytest.fixture()
def memory_b() -> Memory:
    return Memory(
        user_id="alice",
        category=MemoryCategory.GOALS,
        content="Wants to learn Rust",
        importance=0.7,
        confidence=0.8,
        embedding=_unit_vec(4, 1),
    )


class TestInMemoryVectorStore:
    @pytest.mark.asyncio
    async def test_add_and_search_exact(self, store, memory_a) -> None:
        await store.add(memory_a)
        results = await store.search(
            user_id="alice",
            query_embedding=_unit_vec(4, 0),
            top_k=5,
            threshold=0.9,
        )
        assert len(results) == 1
        assert results[0].id == memory_a.id

    @pytest.mark.asyncio
    async def test_threshold_filters(self, store, memory_a, memory_b) -> None:
        await store.add(memory_a)
        await store.add(memory_b)
        # Query perfectly matches memory_a — memory_b should be filtered out
        results = await store.search(
            user_id="alice",
            query_embedding=_unit_vec(4, 0),
            top_k=5,
            threshold=0.9,
        )
        assert all(r.id == memory_a.id for r in results)

    @pytest.mark.asyncio
    async def test_user_isolation(self, store, memory_a) -> None:
        await store.add(memory_a)
        results = await store.search(
            user_id="bob",  # Different user
            query_embedding=_unit_vec(4, 0),
            top_k=5,
            threshold=0.0,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self, store, memory_a) -> None:
        await store.add(memory_a)
        await store.delete(memory_a.id)
        results = await store.search(
            user_id="alice",
            query_embedding=_unit_vec(4, 0),
            top_k=5,
            threshold=0.0,
        )
        assert results == []
