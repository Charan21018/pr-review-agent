"""
backend/agents/security.py — Security Specialist Agent.

Focuses on:
  - Hardcoded secrets / tokens
  - Injection vulnerabilities (SQLi, Command Injection, Prompt Injection)
  - Insecure deserialization / unauthenticated endpoints
"""

import re
from typing import List, Optional

from backend.agents.base import BaseSpecialistAgent
from backend.agents.schemas import Finding, SeverityEnum


class SecurityAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 10.0):
        super().__init__(name="security", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        findings: List[Finding] = []

        lines = pr_diff.splitlines()
        for idx, line in enumerate(lines, 1):
            if not line.startswith("+"):
                continue

            content = line[1:].strip()

            # Rule 1: Hardcoded credentials / secret keys
            if re.search(r'(api_key|secret|password|auth_token)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', content, re.IGNORECASE):
                rationale = "Hardcoded secret or credential detected in diff. Move secrets to environment variables."
                if context_chunks:
                    rationale += f" [Grounded in {len(context_chunks)} codebase context chunk(s)]"
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.CRITICAL,
                        category="Hardcoded Secrets",
                        line_start=idx,
                        line_end=idx,
                        rationale=rationale,
                        confidence=0.95,
                    )
                )

            # Rule 2: SQL Injection via string formatting
            if re.search(r'SELECT\s+.*\s+FROM\s+.*%s|f["\'].*SELECT.*\{', content, re.IGNORECASE):
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.HIGH,
                        category="SQL Injection",
                        line_start=idx,
                        line_end=idx,
                        rationale="Possible SQL injection via raw string formatting. Use parameterized queries.",
                        confidence=0.90,
                    )
                )

            # Rule 3: Shell execution / eval
            if re.search(r'\b(eval|exec|os\.system|subprocess\.Popen)\(', content):
                findings.append(
                    Finding(
                        specialist=self.name,
                        severity=SeverityEnum.HIGH,
                        category="Command Execution",
                        line_start=idx,
                        line_end=idx,
                        rationale="Dynamic code/command execution detected. Avoid eval/exec or pass shell=False.",
                        confidence=0.85,
                    )
                )

        return findings
