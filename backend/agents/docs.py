"""
backend/agents/docs.py — Documentation Specialist Agent.

Focuses on:
  - Missing docstrings for new public classes/methods
  - Outdated API comments
  - TODO/FIXME markers left in code
"""

import re
from typing import List, Optional

from backend.agents.base import BaseSpecialistAgent
from backend.agents.schemas import Finding, SeverityEnum


class DocsAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 10.0):
        super().__init__(name="docs", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        findings: List[Finding] = []

        lines = pr_diff.splitlines()
        for idx, line in enumerate(lines, 1):
            if not line.startswith("+"):
                continue

            content = line[1:].strip()

            # Rule 1: TODO / FIXME left in diff
            if re.search(r'\b(TODO|FIXME|XXX|HACK)\b', content):
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.INFO,
                        category="Documentation Marker",
                        line_start=idx,
                        line_end=idx,
                        rationale="Unresolved TODO/FIXME comment added. Ensure issue tracker reference is included.",
                        confidence=0.85,
                    )
                )

        return findings
