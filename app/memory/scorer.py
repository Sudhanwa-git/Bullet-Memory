"""
Importance Scorer — decides whether an extracted memory is worth persisting.

The scorer is intentionally simple: it applies a configurable threshold to the
importance value already provided by the LLM extractor.

Future improvements could apply rule-based boosts, recency decay, or ML scoring.
"""
from __future__ import annotations

import structlog

from app.core.config import settings
from app.memory.models import ExtractedMemory

logger = structlog.get_logger(__name__)


class ImportanceScorer:
    """
    Filters extracted memory candidates against a configurable importance threshold.

    Only memories that pass the threshold proceed to embedding and persistence.
    """

    def __init__(self, threshold: float | None = None) -> None:
        self._threshold = threshold if threshold is not None else settings.IMPORTANCE_THRESHOLD

    def filter(self, candidates: list[ExtractedMemory]) -> list[ExtractedMemory]:
        """
        Return only the candidates whose importance meets the threshold.
        Logs each rejected candidate for observability.
        """
        accepted: list[ExtractedMemory] = []
        for candidate in candidates:
            if candidate.importance >= self._threshold:
                accepted.append(candidate)
            else:
                logger.debug(
                    "scorer.rejected",
                    content=candidate.content[:60],
                    importance=candidate.importance,
                    threshold=self._threshold,
                )

        logger.info(
            "scorer.filter.done",
            total=len(candidates),
            accepted=len(accepted),
            rejected=len(candidates) - len(accepted),
        )
        return accepted
