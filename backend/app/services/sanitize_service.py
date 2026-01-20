"""
Sanitization Service - Validates and cleans user input before sending to Claude.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Maximum query length
MAX_QUERY_LENGTH = 500

# Suspicious patterns that might indicate prompt injection
SUSPICIOUS_PATTERNS = [
    r"ignore.*instruction",
    r"ignore.*previous",
    r"ignore.*above",
    r"forget.*instruction",
    r"forget.*previous",
    r"disregard.*instruction",
    r"system\s*prompt",
    r"you\s*are\s*now",
    r"pretend\s*to\s*be",
    r"act\s*as\s*if",
    r"new\s*instruction",
    r"override",
    r"execute.*code",
    r"run.*command",
    r"<script",
    r"javascript:",
    r"\beval\b",
    r"\bexec\b",
]


class SanitizeService:
    """Service for sanitizing and validating user queries."""

    def sanitize_query(self, query: str) -> Tuple[str, bool, str]:
        """
        Sanitize a user query for safe processing.

        Args:
            query: Raw user input

        Returns:
            Tuple of (sanitized_query, is_valid, error_message)
        """
        if not query:
            return "", False, "Query cannot be empty"

        # Strip whitespace
        query = query.strip()

        # Check length
        if len(query) > MAX_QUERY_LENGTH:
            return "", False, f"Query too long (max {MAX_QUERY_LENGTH} characters)"

        if len(query) < 3:
            return "", False, "Query too short (min 3 characters)"

        # Remove control characters (keep printable ASCII and common unicode)
        sanitized = ''.join(c for c in query if ord(c) >= 32 or c in '\n\t')

        # Check for suspicious patterns
        query_lower = sanitized.lower()
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, query_lower):
                logger.warning(f"Suspicious pattern detected in query: {pattern}")
                # Don't reject, but log it - the query might be legitimate
                # We rely on Claude's system prompt to handle these

        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())

        # Basic profanity/abuse check could go here
        # For now, we trust the input and let Claude handle edge cases

        return sanitized, True, ""

    def is_valid_player_name(self, name: str) -> bool:
        """Check if a string looks like a valid player name."""
        if not name or len(name) < 2:
            return False

        # Should contain at least some letters
        if not any(c.isalpha() for c in name):
            return False

        # Shouldn't be all numbers
        if name.replace(" ", "").isdigit():
            return False

        return True


# Singleton instance
sanitize_service = SanitizeService()
