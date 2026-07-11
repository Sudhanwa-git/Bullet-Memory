"""
Tests for the Prediction Engine's query-building logic.

Validates that predictive queries are correctly derived from working memory state.
"""

from __future__ import annotations

from app.memory.prediction import PredictionEngine
from app.memory.working_memory import WorkingMemoryState


class TestPredictionEngineQueryBuilder:
    def test_empty_state_returns_no_queries(self):
        state = WorkingMemoryState("s1", "a1", "u1")
        queries = PredictionEngine._build_predictive_queries(state)
        assert queries == []

    def test_goal_alone_produces_one_query(self):
        state = WorkingMemoryState("s1", "a1", "u1", goal="Deploy service")
        queries = PredictionEngine._build_predictive_queries(state)
        assert "Deploy service" in queries

    def test_pending_step_produces_queries(self):
        state = WorkingMemoryState("s1", "a1", "u1", goal="Deploy service")
        state.pending_steps = ["Run tests", "Push to registry"]
        queries = PredictionEngine._build_predictive_queries(state)
        # Should include goal, first pending step, and combined
        assert "Deploy service" in queries
        assert "Run tests" in queries
        assert any("Deploy service" in q and "Run tests" in q for q in queries)

    def test_queries_are_deduplicated(self):
        state = WorkingMemoryState("s1", "a1", "u1", goal="Do X")
        state.pending_steps = ["Do X"]  # Same as goal — should deduplicate
        queries = PredictionEngine._build_predictive_queries(state)
        assert queries.count("Do X") == 1

    def test_scratchpad_short_is_ignored(self):
        state = WorkingMemoryState("s1", "a1", "u1", goal="Deploy")
        state.scratchpad = "ok"  # Too short (< 20 chars)
        queries = PredictionEngine._build_predictive_queries(state)
        # Only the goal should be there, not the scratchpad
        assert len(queries) == 1

    def test_scratchpad_long_is_included(self):
        state = WorkingMemoryState("s1", "a1", "u1", goal="Deploy")
        state.scratchpad = "I need to check if the database connection string is correct first."
        queries = PredictionEngine._build_predictive_queries(state)
        assert any("database" in q.lower() for q in queries)
