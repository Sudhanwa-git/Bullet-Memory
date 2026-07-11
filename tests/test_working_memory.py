"""
Tests for the WorkingMemoryState model.

Validates serialization, deserialization, and state transitions.
"""

from __future__ import annotations

from app.memory.working_memory import WorkingMemoryState


class TestWorkingMemoryState:
    def test_create_defaults(self):
        state = WorkingMemoryState("s1", "agent-1", "user-1", goal="Deploy app")
        assert state.goal == "Deploy app"
        assert state.plan == []
        assert state.completed_steps == []
        assert state.pending_steps == []
        assert state.variables == {}
        assert state.tool_outputs == []
        assert state.scratchpad == ""

    def test_round_trip_serialization(self):
        state = WorkingMemoryState("s1", "agent-1", "user-1", goal="Test goal")
        state.plan = ["step1", "step2"]
        state.variables = {"key": "value"}
        state.scratchpad = "some reasoning"

        data = state.to_dict()
        restored = WorkingMemoryState.from_dict(data)

        assert restored.session_id == state.session_id
        assert restored.agent_id == state.agent_id
        assert restored.user_id == state.user_id
        assert restored.goal == state.goal
        assert restored.plan == state.plan
        assert restored.variables == state.variables
        assert restored.scratchpad == state.scratchpad

    def test_checkpoint_id_is_unique(self):
        s1 = WorkingMemoryState("s1", "a", "u")
        s2 = WorkingMemoryState("s2", "a", "u")
        assert s1.checkpoint_id != s2.checkpoint_id

    def test_to_dict_keys(self):
        state = WorkingMemoryState("s1", "agent-1", "user-1")
        d = state.to_dict()
        required_keys = [
            "session_id", "agent_id", "user_id", "goal", "plan",
            "completed_steps", "pending_steps", "variables",
            "tool_outputs", "scratchpad", "checkpoint_id",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"
