"""
Tests for the Episode and Reflection Engine.

Validates episode creation, event logging, completion, and failure handling.
"""

from __future__ import annotations

from app.memory.episodes import Episode, EpisodeEngine, EpisodeStatus


class TestEpisodeEngine:
    def test_create_episode(self):
        engine = EpisodeEngine()
        ep = engine.create("sess-1", "user-1", "agent-1", goal="Build feature X")
        assert ep.goal == "Build feature X"
        assert ep.status == EpisodeStatus.ACTIVE
        assert ep.timeline == []

    def test_log_event(self):
        engine = EpisodeEngine()
        ep = engine.create("sess-1", "user-1", "agent-1", goal="Test goal")
        engine.log_event(ep.episode_id, "tool_call", "Called search API")
        assert len(ep.timeline) == 1
        assert ep.timeline[0].event_type == "tool_call"
        assert ep.timeline[0].content == "Called search API"

    def test_complete_episode(self):
        engine = EpisodeEngine()
        ep = engine.create("sess-1", "user-1", "agent-1", goal="Deploy")
        engine.log_event(ep.episode_id, "step", "Build done")
        result = engine.complete(ep.episode_id, "Deployed successfully")
        assert result.status == EpisodeStatus.COMPLETED
        assert result.outcome == "Deployed successfully"
        assert result.ended_at is not None

    def test_fail_episode(self):
        engine = EpisodeEngine()
        ep = engine.create("sess-1", "user-1", "agent-1", goal="Deploy")
        result = engine.fail(ep.episode_id, "Connection timeout")
        assert result.status == EpisodeStatus.FAILED
        assert "FAILED" in result.outcome
        assert "Connection timeout" in result.outcome

    def test_log_event_unknown_episode_is_noop(self):
        engine = EpisodeEngine()
        # Should not raise — just warns
        engine.log_event("nonexistent-id", "tool_call", "Should be ignored")

    def test_episode_to_narrative(self):
        ep = Episode("ep-1", "sess-1", "user-1", "agent-1", goal="Ship it")
        ep.add_event("step", "Ran tests")
        ep.add_event("tool_call", "Called deploy API")
        ep.outcome = "Shipped!"
        narrative = ep.to_narrative()
        assert "Ship it" in narrative
        assert "Ran tests" in narrative
        assert "Called deploy API" in narrative
        assert "Shipped!" in narrative

    def test_evict_removes_from_cache(self):
        engine = EpisodeEngine()
        ep = engine.create("sess-1", "user-1", "agent-1", goal="Test")
        episode_id = ep.episode_id
        engine.evict(episode_id)
        assert engine.get(episode_id) is None
