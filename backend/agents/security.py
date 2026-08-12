"""
backend/agents/security.py — Security Specialist Agent (LLM-powered).

Uses GPT-4o to identify:
- Hardcoded secrets/tokens
- Injection vulnerabilities (SQLi, Command, Prompt)
- Insecure deserialization / unauthenticated endpoints
- SSRF, path traversal, exposed secrets in logs
"""
import json
from typing import List, Optional

from backend.agents.base import BaseSpecialistAgent
from backend.agents.schemas import Finding, SeverityEnum
from backend.tools.llm_client import chat_completion_json
from backend.tools.model_router import get_model_for_agent
from backend.prompts.registry import render, PROMPT_VERSION


class SecurityAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 60.0):
        super().__init__(name="security", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        context_section = ""
        if context_chunks:
            context_section = "## Relevant Codebase Context\n" + "\n---\n".join(context_chunks[:5])

        user_prompt = render(
            "security.user",
            prompt_version=PROMPT_VERSION,
            pr_diff=pr_diff[:12000],  # token guard
            context_section=context_section,
        )

        parsed, meta = await chat_completion_json(
            model=get_model_for_agent("security"),
            system_prompt=render("security.system") if False else _get_system("security"),
            user_prompt=user_prompt,
            temperature=0.1,
            agent_name=self.name,
        )
        self.last_call_meta = meta

        return _parse_findings(parsed, specialist=self.name, context_chunks=context_chunks)


class QualityAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 60.0):
        super().__init__(name="quality", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        context_section = ""
        if context_chunks:
            context_section = "## Relevant Codebase Context\n" + "\n---\n".join(context_chunks[:5])

        user_prompt = render(
            "quality.user",
            prompt_version=PROMPT_VERSION,
            pr_diff=pr_diff[:12000],
            context_section=context_section,
        )

        parsed, meta = await chat_completion_json(
            model=get_model_for_agent("quality"),
            system_prompt=_get_system("quality"),
            user_prompt=user_prompt,
            temperature=0.1,
            agent_name=self.name,
        )
        self.last_call_meta = meta

        return _parse_findings(parsed, specialist=self.name, context_chunks=context_chunks)


class TestsAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 60.0):
        super().__init__(name="tests", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        context_section = ""
        if context_chunks:
            context_section = "## Relevant Codebase Context\n" + "\n---\n".join(context_chunks[:5])

        user_prompt = render(
            "tests.user",
            prompt_version=PROMPT_VERSION,
            pr_diff=pr_diff[:12000],
            context_section=context_section,
        )

        parsed, meta = await chat_completion_json(
            model=get_model_for_agent("tests"),
            system_prompt=_get_system("tests"),
            user_prompt=user_prompt,
            temperature=0.1,
            agent_name=self.name,
        )
        self.last_call_meta = meta

        return _parse_findings(parsed, specialist=self.name, context_chunks=context_chunks)


class DocsAgent(BaseSpecialistAgent):

    def __init__(self, timeout_seconds: float = 60.0):
        super().__init__(name="docs", timeout_seconds=timeout_seconds)

    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        context_section = ""
        if context_chunks:
            context_section = "## Relevant Codebase Context\n" + "\n---\n".join(context_chunks[:5])

        user_prompt = render(
            "docs.user",
            prompt_version=PROMPT_VERSION,
            pr_diff=pr_diff[:12000],
            context_section=context_section,
        )

        parsed, meta = await chat_completion_json(
            model=get_model_for_agent("docs"),
            system_prompt=_get_system("docs"),
            user_prompt=user_prompt,
            temperature=0.1,
            agent_name=self.name,
        )
        self.last_call_meta = meta

        return _parse_findings(parsed, specialist=self.name, context_chunks=context_chunks)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_system(agent_name: str) -> str:
    from backend.prompts.registry import get
    return get(f"{agent_name}.system")


def _parse_findings(
    parsed: dict, specialist: str, context_chunks: Optional[List[str]] = None
) -> List[Finding]:
    """Convert the LLM JSON output into validated Finding objects."""
    findings: List[Finding] = []
    raw_list = parsed.get("findings", []) if isinstance(parsed, dict) else []

    rationale_prefix = ""
    if context_chunks:
        rationale_prefix = f"Grounded in {context_chunks[0][:30]!r}: "

    for item in raw_list:
        try:
            findings.append(
                Finding(
                    specialist=specialist,
                    severity=SeverityEnum(item.get("severity", "INFO")),
                    category=item.get("category", "Unknown"),
                    file_path=item.get("file_path"),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    rationale=rationale_prefix + item.get("rationale", "No rationale provided."),
                    confidence=float(item.get("confidence", 0.5)),
                )
            )
        except Exception:
            pass  # Skip malformed findings silently
    return findings
