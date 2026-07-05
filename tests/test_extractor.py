"""
Tests for the MemoryExtractor JSON parser.
No LLM calls are made — the parser is tested in isolation.
"""
from __future__ import annotations

import pytest

from app.memory.extractor import MemoryExtractor
from app.memory.models import MemoryCategory


class TestExtractorParser:
    """Test the static _parse method without any LLM calls."""

    def test_valid_json(self) -> None:
        raw = """
        [
          {"category": "Technologies", "content": "Python developer", "importance": 0.9, "confidence": 0.95}
        ]
        """
        result = MemoryExtractor._parse(raw)
        assert len(result) == 1
        assert result[0].category == MemoryCategory.TECHNOLOGIES
        assert result[0].content == "Python developer"

    def test_markdown_fence_stripped(self) -> None:
        raw = "```json\n[{\"category\": \"Goals\", \"content\": \"Learn Rust\", \"importance\": 0.7, \"confidence\": 0.8}]\n```"
        result = MemoryExtractor._parse(raw)
        assert len(result) == 1
        assert result[0].category == MemoryCategory.GOALS

    def test_empty_array(self) -> None:
        assert MemoryExtractor._parse("[]") == []

    def test_invalid_json_returns_empty(self) -> None:
        assert MemoryExtractor._parse("not json") == []

    def test_unknown_category_falls_back_to_general(self) -> None:
        raw = '[{"category": "WeirdStuff", "content": "Some fact", "importance": 0.5, "confidence": 0.8}]'
        result = MemoryExtractor._parse(raw)
        assert result[0].category == MemoryCategory.GENERAL

    def test_missing_content_skips_item(self) -> None:
        raw = '[{"category": "Skills", "importance": 0.9}]'
        result = MemoryExtractor._parse(raw)
        assert result == []
