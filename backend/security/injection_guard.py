"""backend/security/injection_guard.py — Prompt injection guard and detection.

Analyzes inputs (PR diffs, titles, comments) for prompt injection payloads
that attempt to bypass safety filters or manipulate review outcomes.
"""
import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Heuristics for detecting prompt injection patterns (case-insensitive)
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
    r"(?i)system\s+override",
    r"(?i)you\s+are\s+now\s+an?\s+assistant",
    r"(?i)forget\s+(?:everything\s+)?you\s+were\s+told",
    r"(?i)new\s+role\s+for\s+the\s+ai",
    r"(?i)markdown\s+injection\s+test",
    r"(?i)stop\s+reviewing\s+and\s+say",
    r"(?i)bypass\s+safety\s+filter",
    r"(?i)override\s+outcome\s+to\s+approved",
    r"(?i)do\s+not\s+report\s+any\s+(?:critical|high|medium|low|security|vulnerability)\s+issues"
]

class InjectionGuard:
    """Utility to run static analysis checking for prompt injections."""

    @staticmethod
    def scan_text(text: str) -> Tuple[bool, float, str]:
        """Scans a block of text for injection attempts.

        Returns:
            (is_injection, confidence, reason)
        """
        if not text:
            return False, 0.0, ""

        matches_found = []
        for pattern in INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                matches_found.append(match.group(0))

        if matches_found:
            confidence = min(0.95, 0.5 + 0.15 * len(matches_found))
            reason = f"Detected injection heuristics matching: {', '.join(matches_found)}"
            logger.warning("InjectionGuard: suspected prompt injection detected: %s", reason)
            return True, confidence, reason

        return False, 0.0, ""
