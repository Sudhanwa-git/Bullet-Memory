"""
Tests for ImportanceScorer.
"""
from __future__ import annotations

import pytest

from app.memory.models import ExtractedMemory, MemoryCategory
from app.memory.scorer import ImportanceScorer


def _make_candidate(importance: float) -> ExtractedMemory:
    return ExtractedMemory(
        category=MemoryCategory.TECHNOLOGIES,
        content="Some fact",
        importance=importance,
        confidence=0.9,
    )


class TestImportanceScorer:
    def test_accepts_above_threshold(self) -> None:
        scorer = ImportanceScorer(threshold=0.5)
        candidates = [_make_candidate(0.6), _make_candidate(0.8)]
        result = scorer.filter(candidates)
        assert len(result) == 2

    def test_rejects_below_threshold(self) -> None:
        scorer = ImportanceScorer(threshold=0.5)
        candidates = [_make_candidate(0.2), _make_candidate(0.4)]
        result = scorer.filter(candidates)
        assert result == []

    def test_accepts_at_threshold(self) -> None:
        scorer = ImportanceScorer(threshold=0.5)
        result = scorer.filter([_make_candidate(0.5)])
        assert len(result) == 1

    def test_mixed_batch(self) -> None:
        scorer = ImportanceScorer(threshold=0.5)
        candidates = [_make_candidate(0.3), _make_candidate(0.7), _make_candidate(0.9)]
        result = scorer.filter(candidates)
        assert len(result) == 2

    def test_empty_input(self) -> None:
        scorer = ImportanceScorer(threshold=0.5)
        assert scorer.filter([]) == []
