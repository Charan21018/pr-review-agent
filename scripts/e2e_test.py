#!/usr/bin/env python
"""scripts/e2e_test.py — End-to-end smoke test for the PR review pipeline.

Runs the full aggregator pipeline (all 4 specialists, in mock-LLM mode since
no OPENAI_API_KEY is required) against the sample diff fixture, with GitHub
posting and the HITL decision mocked out, and prints the resulting outcome.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.aggregator import Aggregator


def run_e2e():
    os.environ.setdefault("GITHUB_REPO", "owner/repo")
    os.environ.setdefault("PR_NUMBER", "1")
    os.environ.setdefault("GITHUB_TOKEN", "mock-token-e2e")

    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests", "fixtures", "sample.diff",
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        diff = f.read()

    mock_gh = MagicMock()
    mock_decision = AsyncMock(return_value={"decision": "APPROVE", "reviewer": "auto", "comments": ""})

    async def _run():
        with patch("backend.api.github_client.GitHubClient", return_value=mock_gh):
            with patch("backend.api.hitl.await_decision", mock_decision):
                aggregator = Aggregator()
                review = await aggregator.run_review(diff)
                if review.recommendation in ("APPROVE", "REQUEST_CHANGES"):
                    print("POSTED")
                else:
                    print("QUEUED_FOR_HUMAN")
                return review

    asyncio.run(_run())


if __name__ == "__main__":
    run_e2e()
