# AI PR Review Agent — Project Status & Completion Analysis

## What Has Been Built (Milestones M1–M4 ✅ DONE)

| Milestone | Status | What Was Built |
|-----------|--------|----------------|
| **M1** — Spine + Webhook Ingress | ✅ DONE | FastAPI webhook, HMAC signature verification, deduplication, Redis/ARQ queue, DB schema (`code_chunks`, `agent_events`, `reviews`, `findings`) |
| **M2** — Parallel Specialists + Aggregator | ✅ DONE | 4 specialist agents (SecurityAgent, QualityAgent, TestsAgent, DocsAgent), Aggregator with parallel fan-out, deduplication, confidence scoring |
| **M3** — RAG Memory + Code Grounding | ✅ DONE | TigerMemoryClient, CodeIngestor, hybrid vector+FTS search, ContextRetriever with RRF |
| **M4** — Events Spine + Observability | ✅ DONE | EventTracker, CostRepository, BudgetGuard, agent_events persistence |
| **M5** — HITL Gate + GitHub Review Posting | ✅ DONE | HITL gate, GitHub review posting with retry/circuit-breaker/DLQ, and tests all in place |

---

## Current Test Status (0 FAILING / 37 passing)

Fixed 2026-08-11:
- Mock LLM responses (`backend/tools/llm_client.py`) now pattern-match the actual diff text per specialist instead of returning a fixed canned response, so categories match what each test diff actually contains and clean diffs correctly yield zero findings.
- Root cause of the category mismatches was a substring-collision bug: the fallback inferred which specialist was calling by searching for "quality"/"test"/"doc" inside the *system prompt text*, but the tests/docs system prompts both contain the word "quality" too (e.g. "test quality and coverage review"), so they were silently misclassified. Fixed by passing `agent_name` explicitly through `chat_completion`/`chat_completion_json` instead of guessing from prompt text.
- `backend/agents/security.py::_parse_findings` now prepends `"Grounded in ..."` to the rationale when `context_chunks` were supplied.
- `backend/api/github_client.py::GitHubClient.__init__` no longer raises when `GITHUB_TOKEN` is unset; `post_review()` no-ops (with a log warning) in that case, and otherwise wraps the real call with exponential-backoff retry (3 attempts) plus an in-process circuit breaker (opens after 3 consecutive failures, 30s cooldown) that prints `[DLQ] Review posting failed for PR {pull_number}` instead of raising.
- `backend/agents/aggregator.py`: a genuine HITL timeout (no human decision recorded) now keeps the recommendation as `ESCALATE_TO_HUMAN` instead of silently defaulting to `APPROVE` — the old fallback was an auto-approve safety bug.
- Added `tests/test_github_client.py` and `scripts/e2e_test.py` (prints `POSTED`/`QUEUED_FOR_HUMAN`).

<details>
<summary>Historical failure analysis (pre-fix, kept for reference)</summary>

### Group 1: Mock Agent Category Mismatches (6 failures)
**Root cause:** `_generate_mock_llm_response()` in `backend/tools/llm_client.py` returns **hardcoded** findings that don't match what the tests expect when OPENAI_API_KEY is not set.

| Test | Expected Category | Mock Returns |
|------|-------------------|-------------|
| `test_detects_sql_injection` | `"SQL Injection"` | `"Command Injection"` |
| `test_detects_exec` | `"Command Execution"` | `"Command Injection"` |
| `test_detects_swallowed_exception` | `"Swallowed Exception"` | `"Debug Statement"` |
| `test_detects_missing_unit_tests` | `"Missing Unit Tests"` | `"Test Coverage"` |
| `test_detects_skipped_test` | `"Skipped Test"` | `"Test Coverage"` |
| `test_detects_todo_comment` | `"Documentation Marker"` | `"Documentation"` |

### Group 2: Aggregator / GitHubClient crashes (2 failures)
**Root cause:** `GitHubClient()` raises `ValueError` when `GITHUB_TOKEN` env var is not set. The aggregator calls `GitHubClient()` unconditionally during the ESCALATE_TO_HUMAN path — with no mock/graceful fallback in tests.

- `TestAggregator::test_sample_diff_aggregation` — crashes when aggregator tries to call GitHubClient
- `TestAggregator::test_clean_diff_approval` — same crash

### Group 3: "Grounded in" rationale not present (1 failure)
**Root cause:** The mock response in `_generate_mock_llm_response("security")` returns a hardcoded rationale that doesn't include "Grounded in" even when `context_chunks` are passed.

- `test_memory.py::test_specialist_grounding` — expects `"Grounded in" in findings[0].rationale`

</details>

---

## M5 requirements — now resolved

| File | Status | Notes |
|------|--------|-------|
| `tests/test_hitl.py` | ✅ Covered | Equivalent coverage already existed in `tests/test_hitl_endpoint.py` + `tests/test_aggregator_hitl_integration.py` |
| `tests/test_github_client.py` | ✅ Added | Approve/request-changes/no-token/retry-then-DLQ cases |
| `scripts/e2e_test.py` | ✅ Added | Prints `POSTED` or `QUEUED_FOR_HUMAN` |
| Circuit breaker on GitHub API | ✅ Wired | Lightweight sync breaker in `backend/api/github_client.py` (opens after 3 consecutive failures, 30s cooldown) — `post_review()` is called synchronously from the aggregator, so it doesn't reuse the async `backend/reliability/circuit_breaker.py` registry directly |
| Dead-letter queue after 3 failures | ✅ Implemented | Prints `[DLQ] Review posting failed for PR {pull_number}` instead of raising |
| Exponential backoff on GitHub API | ✅ Wired | 3 attempts, 1s/2s/4s backoff, synchronous (same reasoning as circuit breaker above) |

<details>
<summary>Original Claude prompt used to scope this work (historical, already applied)</summary>

```
You are working on an AI PR Review Agent Python project. The project uses FastAPI, SQLAlchemy, asyncpg, and OpenAI. Here is what is done and what needs to be fixed/completed.

## Project Structure (key files)
- backend/agents/security.py — SecurityAgent, QualityAgent, TestsAgent, DocsAgent (all in one file)
- backend/agents/aggregator.py — Aggregator that fan-outs to all specialists
- backend/agents/schemas.py — Pydantic models: Finding, AggregatedReview, SeverityEnum
- backend/agents/base.py — BaseSpecialistAgent with run_with_timeout()
- backend/tools/llm_client.py — OpenAI client with mock fallback
- backend/api/github_client.py — GitHubClient.post_review()
- backend/api/hitl.py — router (POST /hitl), await_decision()
- backend/reliability/circuit_breaker.py — CircuitBreaker class (exists, not wired)
- backend/reliability/retry.py — retry_with_backoff() (exists, not wired)
- tests/test_agents.py — Acceptance tests for all agents
- tests/test_memory.py — Memory and grounding tests

## Task 1: Fix mock agent responses in backend/tools/llm_client.py

The function `_generate_mock_llm_response(agent_name)` returns hardcoded findings that don't match test expectations. Fix it so:

- When agent_name contains "security", the mock MUST return findings that include ALL of:
  - A finding with category: "Hardcoded Secrets" and severity: "CRITICAL"
  - A finding with category: "SQL Injection"
  - A finding with category: "Command Execution"

- When agent_name contains "quality", the mock MUST return findings that include ALL of:
  - A finding with category: "Swallowed Exception"
  - A finding with category: "Debug Statement"

- When agent_name contains "test", the mock MUST return findings that include ALL of:
  - A finding with category: "Missing Unit Tests"
  - A finding with category: "Skipped Test"

- When agent_name contains "doc", the mock MUST return findings that include ALL of:
  - A finding with category: "Documentation Marker"

## Task 2: Fix mock agent to include "Grounded in" in rationale when context_chunks are passed

In backend/agents/security.py (and all other agent classes), when context_chunks is not empty,
the rationale of findings returned by the mock must include the text "Grounded in".

Since the mock response in _generate_mock_llm_response is static and cannot know about context_chunks,
fix this by post-processing findings in _parse_findings() or in the agent's analyze() method:
if context_chunks were provided, prepend "Grounded in [context_chunks[0][:30]]" to each finding's rationale.

Specifically fix backend/agents/security.py so that if context_chunks is not empty,
each returned Finding's rationale starts with "Grounded in".

## Task 3: Fix GitHubClient to not raise ValueError in tests

In backend/api/github_client.py, __init__ raises ValueError when GITHUB_TOKEN is not set.
In tests, this causes TestAggregator::test_sample_diff_aggregation and
TestAggregator::test_clean_diff_approval to crash.

Fix: Make GitHubClient.__init__ NOT raise — instead, store token = None and only raise
in post_review() if a real call is attempted AND no token is set. Or better: if token is None,
post_review() should silently do nothing (return without error).

## Task 4: Wire circuit breaker and retry into GitHubClient

In backend/api/github_client.py, the post_review() method currently makes direct GitHub API
calls with no retry or circuit breaker.

Wire in backend/reliability/circuit_breaker.py and backend/reliability/retry.py:
- Wrap the pr.create_review() call with exponential backoff retry (max 3 attempts, base delay 1s)
- Wrap with a circuit breaker that opens after 3 consecutive failures and rejects calls
- If circuit breaker is open or retries exhausted, log a warning and print
  "[DLQ] Review posting failed for PR {pull_number}" instead of raising

## Task 5: Create tests/test_hitl.py

Create tests/test_hitl.py with these tests:

```python
import pytest
from backend.api.hitl import await_decision, router
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_hitl_post_endpoint_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    import importlib, backend.api.__init__ as api_init
    importlib.reload(api_init)
    resp = client.post("/hitl", json={"review_id": "rev-1", "decision": "APPROVE", "reviewer": "bob", "comments": "ok"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"

def test_hitl_post_endpoint_reject(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    import importlib, backend.api.__init__ as api_init
    importlib.reload(api_init)
    resp = client.post("/hitl", json={"review_id": "rev-2", "decision": "REJECT", "reviewer": "carol", "comments": "nope"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"

@pytest.mark.asyncio
async def test_await_decision_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "empty.db"))
    with pytest.raises(TimeoutError):
        await await_decision("nonexistent-review-id", timeout=1)
```

## Task 6: Create tests/test_github_client.py

Create tests/test_github_client.py with these tests:

```python
import pytest
from unittest.mock import MagicMock, patch
from backend.api.github_client import GitHubClient

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

def test_post_review_no_token_does_not_raise():
    import os
    os.environ.pop("GITHUB_TOKEN", None)
    client = GitHubClient()  # must not raise
    client.post_review("owner/repo", 3, "body", decision="APPROVE")  # must not raise
```

## Task 7: Create scripts/e2e_test.py

Create scripts/e2e_test.py that runs the full pipeline with mocked GitHub/HITL:

```python
#!/usr/bin/env python
"""scripts/e2e_test.py — End-to-end smoke test for the PR review pipeline."""
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.agents.aggregator import Aggregator

def run_e2e():
    os.environ.setdefault("GITHUB_REPO", "owner/repo")
    os.environ.setdefault("PR_NUMBER", "1")
    os.environ.setdefault("GITHUB_TOKEN", "mock-token-e2e")

    with open("tests/fixtures/sample.diff", "r", encoding="utf-8") as f:
        diff = f.read()

    mock_gh = MagicMock()

    async def _run():
        with patch("backend.api.github_client.GitHubClient", return_value=mock_gh):
            with patch("backend.api.hitl.await_decision", return_value={"decision": "APPROVE", "reviewer": "auto", "comments": ""}):
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
```

## Verification

After all fixes, run:
    pytest tests/ -v

Expected result: All 32+ tests pass (0 failures).

Also run the M5 demo command:
    python scripts/e2e_test.py 2>&1 | grep -E "POSTED|QUEUED_FOR_HUMAN|circuit_breaker"

Expected output: POSTED or QUEUED_FOR_HUMAN

The project is Python 3.14, pytest-asyncio in AUTO mode, FastAPI, SQLAlchemy asyncpg for
Postgres, SQLite for local tests. All test files are in the tests/ directory.
```

</details>
