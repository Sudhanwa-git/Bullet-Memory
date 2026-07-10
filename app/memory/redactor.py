"""
PII Redaction utility for Bullet Memory.

Provides a lightweight, regex-based redactor to mask sensitive information
before it gets embedded or stored in the database.
"""
import re

class PIIRedactor:
    """Masks Personally Identifiable Information using Regex."""

    # Simple regex patterns for demonstration
    PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "PHONE": r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
    }

    @classmethod
    def redact(cls, text: str) -> str:
        if not text:
            return text
            
        redacted_text = text
        for label, pattern in cls.PATTERNS.items():
            redacted_text = re.sub(pattern, f"[{label}_REDACTED]", redacted_text)
            
        return redacted_text
