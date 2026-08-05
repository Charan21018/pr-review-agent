"""
tests/conftest.py — shared fixtures for the test suite.

Key fixtures:
  set_test_env   — sets GITHUB_WEBHOOK_SECRET so settings.py reads it correctly
  clear_seen_deliveries — resets in-memory dedup set between tests
  queued_jobs    — injects mock enqueue; records jobs; clears override after test
  client         — async httpx client wired to the FastAPI ASGI app
  make_signature — helper: compute the correct HMAC-SHA256 for a body
  pr_payload     — helper: returns a realistic PR webhook body as bytes
"""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.webhook import _seen_deliveries, app, get_enqueue_fn

TEST_SECRET = "test-secret-for-ci"


# ---------------------------------------------------------------------------
# Environment + state isolation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Override GITHUB_WEBHOOK_SECRET for every test."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)


@pytest.fixture(autouse=True)
def clear_seen_deliveries():
    """Reset the in-memory dedup set before and after each test."""
    _seen_deliveries.clear()
    yield
    _seen_deliveries.clear()


# ---------------------------------------------------------------------------
# Mock queue
# ---------------------------------------------------------------------------

@pytest.fixture
def queued_jobs():
    """
    Inject a mock enqueue function that records jobs in a list instead of
    hitting Redis. Cleans up the dependency override after the test.
    """
    jobs: list[dict] = []

    async def _mock_enqueue(payload: dict) -> str:
        job_id = f"mock-job-{len(jobs) + 1}"
        jobs.append({"job_id": job_id, "payload": payload})
        return job_id

    app.dependency_overrides[get_enqueue_fn] = lambda: _mock_enqueue
    yield jobs
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Async HTTPX client wired to the FastAPI ASGI app (no real server needed)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_signature(body: bytes, secret: str = TEST_SECRET) -> str:
    """Compute the GitHub-style HMAC-SHA256 signature for a request body."""
    h = hmac.new(secret.encode(), body, hashlib.sha256)
    return "sha256=" + h.hexdigest()


def pr_payload(pr_number: int = 42, repo: str = "owner/repo") -> bytes:
    """Return a realistic GitHub pull_request webhook body."""
    return json.dumps(
        {
            "action": "opened",
            "pull_request": {
                "number": pr_number,
                "title": f"feat: add feature #{pr_number}",
                "head": {"sha": "abc123def456"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": repo},
        }
    ).encode()
