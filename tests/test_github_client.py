import os
import pytest
from unittest.mock import MagicMock, patch

import backend.api.github_client as github_client
from backend.api.github_client import GitHubClient


@pytest.fixture(autouse=True)
def _reset_circuit_breaker(monkeypatch):
    """The module-level circuit breaker state persists across tests; reset it
    so one test's failures don't short-circuit a later test's real call."""
    monkeypatch.setattr(github_client, "_circuit_failure_count", 0)
    monkeypatch.setattr(github_client, "_circuit_opened_at", None)


def test_post_review_approve(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    client = GitHubClient()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    with patch.object(client.client, "get_repo", return_value=mock_repo):
        client.post_review("owner/repo", 1, "LGTM", decision="APPROVE")
    mock_pr.create_review.assert_called_once_with(event="APPROVE", body="LGTM")


def test_post_review_request_changes(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    client = GitHubClient()
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    with patch.object(client.client, "get_repo", return_value=mock_repo):
        client.post_review("owner/repo", 2, "Issues found", decision="REQUEST_CHANGES")
    mock_pr.create_review.assert_called_once_with(event="REQUEST_CHANGES", body="Issues found")


def test_post_review_no_token_does_not_raise(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    client = GitHubClient()  # must not raise
    client.post_review("owner/repo", 3, "body", decision="APPROVE")  # must not raise


def test_post_review_retries_then_dlq_on_persistent_failure(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    client = GitHubClient()
    mock_repo = MagicMock()
    mock_repo.get_pull.side_effect = RuntimeError("GitHub API unavailable")
    with patch.object(client.client, "get_repo", return_value=mock_repo):
        with patch("backend.api.github_client.time.sleep"):  # skip real backoff delay
            client.post_review("owner/repo", 4, "body", decision="APPROVE")  # must not raise
    assert mock_repo.get_pull.call_count == 3  # exhausted all retry attempts
