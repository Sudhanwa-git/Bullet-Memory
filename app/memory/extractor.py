"""
Memory Extractor — converts conversation text into structured ExtractedMemory candidates.

Uses the configured LLM with structured JSON output.
"""

from __future__ import annotations

import json

import structlog

from app.adapters.llm import LLMAdapter
from app.core.prompts import EXTRACTION_SYSTEM_PROMPT
from app.memory.models import ExtractedMemory, MemoryCategory

logger = structlog.get_logger(__name__)


class MemoryExtractor:
    """
    Calls the LLM to extract durable, structured knowledge from a conversation turn.

    Returns a list of ExtractedMemory candidates.
    The caller (MemoryService) is responsible for scoring and persisting them.
    """

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    async def extract(
        self,
        user_message: str,
        assistant_response: str,
        source_text: str | None = None,
    ) -> list[ExtractedMemory]:
        conversation = f"User: {user_message}\n\nAssistant: {assistant_response}"
        actual_source = source_text or conversation

        logger.debug("extractor.extract.start", chars=len(conversation))

        raw = await self._llm.complete(
            system=EXTRACTION_SYSTEM_PROMPT,
            user=conversation,
        )

        candidates = self._parse(raw, source_text=actual_source)
        logger.info("extractor.extract.done", candidates=len(candidates))
        return candidates

    # ── Parsing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(raw: str, source_text: str | None = None) -> list[ExtractedMemory]:
        """
        Robustly parse the LLM JSON response into ExtractedMemory objects.
        Handles:
        - Plain JSON array: [{"category": ...}, ...]
        - Wrapped objects:  {"memories": [...]} or {"data": [...]}
        - Markdown fences around the JSON
        Skips malformed or unknown-category items rather than crashing.
        """
        try:
            # Strip markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Drop first (```json) and last (```) lines
                cleaned = "\n".join(lines[1:]).rstrip("`").strip()

            data = json.loads(cleaned)

            # Local LLMs sometimes wrap the array: {"memories": [...]}
            # or return a single object when only one memory is found
            if isinstance(data, dict):
                # Try to find the first list value in the dict (e.g. {"memories": [...]})
                found_list = None
                for v in data.values():
                    if isinstance(v, list):
                        found_list = v
                        break

                if found_list is not None:
                    data = found_list
                elif "content" in data:
                    # Single raw memory object — wrap in a list
                    data = [data]
                else:
                    logger.warning("extractor.parse.unexpected_dict", keys=list(data.keys()))
                    return []

            if not isinstance(data, list):
                logger.warning("extractor.parse.unexpected_type", type=type(data).__name__)
                return []

            results: list[ExtractedMemory] = []
            for item in data:
                try:
                    category_raw = item.get("category", "General")
                    # Normalise category string
                    try:
                        category = MemoryCategory(category_raw)
                    except ValueError:
                        category = MemoryCategory.GENERAL

                    results.append(
                        ExtractedMemory(
                            category=category,
                            content=str(item["content"]),
                            importance=float(item.get("importance", 0.5)),
                            confidence=float(item.get("confidence", 0.8)),
                            source_text=source_text,
                            tags=item.get("tags", []),
                        )
                    )
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning("extractor.parse.item_skipped", error=str(e), item=item)

            return results

        except json.JSONDecodeError as e:
            logger.error("extractor.parse.json_error", error=str(e), raw=raw[:200])
            return []
