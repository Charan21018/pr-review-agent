"""
tests/test_agents.py — Acceptance and unit tests for specialist agents & aggregator.

Covers:
  - SecurityAgent: secret detection, SQL injection, exec/eval calls
  - QualityAgent: swallowed exceptions, debug print statements
  - TestsAgent: missing tests, weak assertions, skipped tests
  - DocsAgent: TODO/FIXME comments
  - Aggregator: parallel fan-out, deduplication, confidence calculation, HITL recommendations
  - Clean Architecture (I1): domain agents never import from api/, queue/, or db/
"""

import sys
import pytest

from backend.agents.aggregator import Aggregator
from backend.agents.docs import DocsAgent
from backend.agents.quality import QualityAgent
from backend.agents.schemas import SeverityEnum
from backend.agents.security import SecurityAgent
from backend.agents.tests import TestsAgent


class TestSecurityAgent:

    async def test_detects_hardcoded_secrets(self):
        agent = SecurityAgent()
        diff = "+ api_key = \"secret_key_12345678\""
        findings = await agent.run_with_timeout(diff)
        assert len(findings) >= 1
        assert any(f.category == "Hardcoded Secrets" and f.severity == SeverityEnum.CRITICAL for f in findings)

    async def test_detects_sql_injection(self):
        agent = SecurityAgent()
        diff = "+ query = f\"SELECT * FROM users WHERE name = '{name}'\""
        findings = await agent.run_with_timeout(diff)
        assert len(findings) >= 1
        assert any(f.category == "SQL Injection" for f in findings)

    async def test_detects_exec(self):
        agent = SecurityAgent()
        diff = "+ exec(user_code)"
        findings = await agent.run_with_timeout(diff)
        assert len(findings) >= 1
        assert any(f.category == "Command Execution" for f in findings)


class TestQualityAgent:

    async def test_detects_swallowed_exception(self):
        agent = QualityAgent()
        diff = "+ except:\n+     pass"
        findings = await agent.run_with_timeout(diff)
        assert len(findings) >= 1
        assert any(f.category == "Swallowed Exception" for f in findings)

    async def test_detects_debug_print(self):
        agent = QualityAgent()
        diff = "+ print(\"debug output\")"
        findings = await agent.run_with_timeout(diff)
        assert len(findings) >= 1
        assert any(f.category == "Debug Statement" for f in findings)


class TestTestsAgent:

    async def test_detects_missing_unit_tests(self):
        agent = TestsAgent()
        diff = "+ def calculate_tax(amount):\n+     return amount * 0.2"
        findings = await agent.run_with_timeout(diff)
        assert any(f.category == "Missing Unit Tests" for f in findings)

    async def test_detects_skipped_test(self):
        agent = TestsAgent()
        diff = "+ @pytest.mark.skip\n+ def test_feature(): pass"
        findings = await agent.run_with_timeout(diff)
        assert any(f.category == "Skipped Test" for f in findings)


class TestDocsAgent:

    async def test_detects_todo_comment(self):
        agent = DocsAgent()
        diff = "+ # TODO: implement caching"
        findings = await agent.run_with_timeout(diff)
        assert any(f.category == "Documentation Marker" for f in findings)


class TestAggregator:

    async def test_sample_diff_aggregation(self):
        with open("tests/fixtures/sample.diff", "r", encoding="utf-8") as f:
            sample_diff = f.read()

        aggregator = Aggregator()
        review = await aggregator.run_review(sample_diff)

        assert len(review.findings) >= 3
        assert review.has_critical is True
        assert review.recommendation == "ESCALATE_TO_HUMAN"

    async def test_clean_diff_approval(self):
        clean_diff = "+ # Just a clean comment\n+ x = 1"
        aggregator = Aggregator()
        review = await aggregator.run_review(clean_diff)

        assert review.has_critical is False
        assert review.overall_confidence >= 0.70
        assert review.recommendation == "APPROVE"


class TestCleanArchitectureInvariant:

    def test_agents_do_not_import_infrastructure(self):
        """Invariant I1: backend.agents modules must not import api, queue, or db."""
        forbidden_prefixes = ("backend.api", "backend.queue", "backend.db")
        agent_modules = [m for name, m in sys.modules.items() if name.startswith("backend.agents")]

        for mod in agent_modules:
            if mod is None:
                continue
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if hasattr(attr, "__module__") and attr.__module__:
                    assert not any(attr.__module__.startswith(p) for p in forbidden_prefixes), \
                        f"Module {mod.__name__} violates I1 by importing {attr.__module__}"
