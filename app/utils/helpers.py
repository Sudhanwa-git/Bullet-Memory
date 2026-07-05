"""
Utility helpers.

Kept intentionally small — heavy logic belongs in the memory or core packages.
"""
from __future__ import annotations

import hashlib
import re


def truncate(text: str, max_chars: int = 100) -> str:
    """Truncate text for log display."""
    return text if len(text) <= max_chars else text[:max_chars] + "…"


def sanitise_user_id(user_id: str) -> str:
    """Remove characters that are unsafe in file paths or collection names."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)


def short_hash(text: str, length: int = 8) -> str:
    """Return a short deterministic hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()[:length]
