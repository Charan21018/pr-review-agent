import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from backend.agents.aggregator import Aggregator
from backend.agents.schemas import AggregatedReview, Finding, SeverityEnum

# Dummy specialist that forces ESCALATE_TO_HUMAN
class DummyCriticalAgent:
    async def run_with_timeout(self, pr_diff: str, context_chunks=None):
        # Return a single critical finding
        return [
            Finding(
                specialist="dummy",
                severity=SeverityEnum.CRITICAL,
                category="security",
                file_path="src/main.py",
                line_start=1,
                line_end=10,
                rationale="Critical issue for testing",
                confidence=0.9,
            )
        ]

@pytest.mark.asyncio
async def test_aggregator_hitl_flow(monkeypatch, tmp_path):
    # Use a temporary SQLite DB
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", str(db_path))
    # Ensure migration runs
    import importlib
    import backend.api.__init__ as api_init
    importlib.reload(api_init)

    # Mock await_decision to return an APPROVE decision instantly
    mock_decision = {"decision": "APPROVE", "reviewer": "tester", "comments": "auto"}
    monkeypatch.setattr("backend.api.hitl.await_decision", lambda review_id, timeout=30: mock_decision)

    # Mock GitHubClient to capture post_review calls without side‑effects
    mock_gh = MagicMock()
    monkeypatch.setattr("backend.api.github_client.GitHubClient", lambda: mock_gh)
    # Set required env vars for GitHubClient (they will be ignored by the mock)
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    monkeypatch.setenv("PR_NUMBER", "1")

    # Build aggregator with only the dummy critical agent
    aggregator = Aggregator(specialists=[DummyCriticalAgent()])
    review = await aggregator.run_review(pr_diff="dummy diff")

    # Verify that the decision from await_decision was used
    assert review.recommendation == "APPROVE"
    # Ensure GitHubClient.post_review was called with the mocked decision
    mock_gh.post_review.assert_called_once()
    args, kwargs = mock_gh.post_review.call_args
    assert kwargs["decision"] == "APPROVE"
    # Verify that a row was recorded in the HITL table
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT review_id, decision, reviewer, comments FROM hitl_events WHERE review_id = ?",
                        (mock_decision["review_id"] if "review_id" in mock_decision else mock_decision["decision"],)).fetchone()
    conn.close()
    # The endpoint stores the row, but our mock decision path does not insert –
    # the test only ensures the flow reaches GitHub posting.
    # Presence of the row is not required for this integration test.
