"""
backend/agents/tests.py — Test Specialist Agent.

Focuses on:
  - Missing unit tests for new functions/endpoints
  - Weak assertions (assert True, assert res is not None)
  - Disabled or skipped tests
"""

import re
from typing import List, Optional

from backend.agents.base import BaseSpecialistAgent
from backend.agents.schemas import Finding, SeverityEnum


class TestsAgent(BaseSpecialistAgent):
    __test__ = False

    def __init__(self, timeout_seconds: float = 10.0):
        super().__init__(name="tests", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        findings: List[Finding] = []

        has_new_function = False
        has_test_addition = False

        lines = pr_diff.splitlines()
        for idx, line in enumerate(lines, 1):
            if not line.startswith("+"):
                continue

            content = line[1:].strip()

            if re.search(r'^\s*def\s+[a-zA-Z0-9_]+\s*\(', content):
                if not content.startswith("def test_"):
                    has_new_function = True
                else:
                    has_test_addition = True

            # Check for weak assertions
            if re.search(r'assert\s+(True|1|len\(.*\)\s*>\s*0)\s*$', content):
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.LOW,
                        category="Weak Assertion",
                        line_start=idx,
                        line_end=idx,
                        rationale="Trivial or weak assertion detected. Assert specific expected values or behaviors.",
                        confidence=0.75,
                    )
                )

            # Check for skipped tests
            if "@pytest.mark.skip" in content or "it.skip" in content:
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.MEDIUM,
                        category="Skipped Test",
                        line_start=idx,
                        line_end=idx,
                        rationale="Skipped test added to codebase. Ensure skipped test is tracked by an issue.",
                        confidence=0.90,
                    )
                )

        if has_new_function and not has_test_addition:
            findings.append(
                Finding(
                    specialist=self.name,
                    severity=SeverityEnum.MEDIUM,
                    category="Missing Unit Tests",
                    line_start=1,
                    line_end=len(lines),
                    rationale="New functions defined in PR without corresponding unit test additions.",
                    confidence=0.70,
                )
            )

        return findings
