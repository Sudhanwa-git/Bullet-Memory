"""
Tests for the ContextBuilder engine.

Ensures token-budget enforcement and memory packing logic are correct.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.memory.context_builder import ContextBuilder
from app.memory.models import Memory, MemoryCategory, SourceType


def _make_memory(content: str, importance: float = 0.8) -> Memory:
    return Memory(
        user_id="test-user",
        category=MemoryCategory.GENERAL,
        source_type=SourceType.CHAT,
        content=content,
        importance=importance,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestContextBuilder:
    def test_empty_memories_returns_empty(self):
        builder = ContextBuilder(max_tokens=500)
        result = builder.build_context("query", [])
        assert result == []

    def test_all_memories_fit_within_budget(self):
        builder = ContextBuilder(max_tokens=500)
        memories = [_make_memory("Short fact.") for _ in range(5)]
        result = builder.build_context("query", memories)
        assert len(result) == 5

    def test_oversized_memories_are_dropped(self):
        builder = ContextBuilder(max_tokens=50)
        # One memory that exceeds the budget on its own
        huge = _make_memory("x" * 300)  # 300 chars ~ 75 tokens
        small = _make_memory("tiny")    # ~1 token
        result = builder.build_context("query", [huge, small])
        # The huge one should be dropped, small should fit
        assert len(result) == 1
        assert result[0].content == "tiny"

    def test_token_estimation_is_deterministic(self):
        builder = ContextBuilder(max_tokens=100)
        mem = _make_memory("Hello world")
        assert builder._estimate_tokens(mem.content) == len(mem.content) // 4

    def test_budget_respected_across_multiple(self):
        # Each memory is ~25 tokens (100 chars), budget is 60 tokens
        builder = ContextBuilder(max_tokens=60)
        memories = [_make_memory("a" * 100) for _ in range(5)]
        result = builder.build_context("query", memories)
        # Only 2 should fit (2 * 25 = 50 <= 60, 3rd would push to 75)
        assert len(result) == 2
