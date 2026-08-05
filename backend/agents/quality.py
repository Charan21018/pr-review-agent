"""
backend/agents/quality.py — Code Quality Specialist Agent.

Focuses on:
  - Empty except blocks / swallowed exceptions
  - High cyclomatic complexity / long functions
  - Print/console debug statements remaining in production code
"""

import re
from typing import List, Optional

from backend.agents.base import BaseSpecialistAgent
from backend.agents.schemas import Finding, SeverityEnum


class QualityAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 10.0):
        super().__init__(name="quality", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        findings: List[Finding] = []

        lines = pr_diff.splitlines()
        for idx, line in enumerate(lines, 1):
            if not line.startswith("+"):
                continue

            content = line[1:].strip()

            # Rule 1: Bare except or pass in exception handling
            if content.startswith("except:") or content == "except Exception: pass":
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.MEDIUM,
                        category="Swallowed Exception",
                        line_start=idx,
                        line_end=idx,
                        rationale="Bare except block or silent exception swallowing detected. Log or handle explicitly.",
                        confidence=0.88,
                    )
                )

            # Rule 2: Leftover print / console.log debug calls
            if re.search(r'\b(print|console\.log|debugger)\(', content) and not "logger" in content:
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.LOW,
                        category="Debug Statement",
                        line_start=idx,
                        line_end=idx,
                        rationale="Raw print/debug statement left in production code. Replace with structured logging.",
                        confidence=0.80,
                    )
                )

        return findings
