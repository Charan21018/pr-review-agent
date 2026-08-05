"""
tests/test_webhook.py — M1 acceptance tests.

Covers:
  TestSignatureVerification — gate 1: HMAC present and valid
  TestIdempotency           — gate 2: X-GitHub-Delivery deduplication
  TestEventFiltering        — gate 3: only pull_request events are queued
  TestJobPayload            — gate 4: correct payload reaches the queue
"""

import json

import pytest

from tests.conftest import make_signature, pr_payload


# ---------------------------------------------------------------------------
# Gate 1 — Signature verification
# ---------------------------------------------------------------------------

class TestSignatureVerification:

    async def test_valid_signature_returns_200(self, client, queued_jobs):
        body = pr_payload()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-valid-sig",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200

    async def test_invalid_signature_returns_401(self, client, queued_jobs):
        body = pr_payload()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": "sha256=deadbeefdeadbeefdeadbeef",
                "X-GitHub-Delivery": "delivery-bad-sig",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid signature"
        assert len(queued_jobs) == 0  # no side-effects before gate passes

    async def test_missing_signature_returns_401(self, client, queued_jobs):
        body = pr_payload()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-GitHub-Delivery": "delivery-no-sig",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Missing X-Hub-Signature-256"
        assert len(queued_jobs) == 0

    async def test_wrong_secret_returns_401(self, client, queued_jobs):
        body = pr_payload()
        wrong_sig = make_signature(body, secret="wrong-secret")
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": wrong_sig,
                "X-GitHub-Delivery": "delivery-wrong-secret",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Gate 2 — Idempotency / deduplication
# ---------------------------------------------------------------------------

class TestIdempotency:

    async def test_duplicate_delivery_returns_duplicate_status(self, client, queued_jobs):
        body = pr_payload()
        headers = {
            "X-Hub-Signature-256": make_signature(body),
            "X-GitHub-Delivery": "delivery-dup-001",
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        r1 = await client.post("/webhook", content=body, headers=headers)
        assert r1.status_code == 200
        assert r1.json()["status"] == "queued"

        r2 = await client.post("/webhook", content=body, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate"

    async def test_duplicate_does_not_enqueue_second_job(self, client, queued_jobs):
        body = pr_payload()
        headers = {
            "X-Hub-Signature-256": make_signature(body),
            "X-GitHub-Delivery": "delivery-dup-002",
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        await client.post("/webhook", content=body, headers=headers)
        await client.post("/webhook", content=body, headers=headers)
        assert len(queued_jobs) == 1  # exactly one job

    async def test_different_delivery_ids_both_queued(self, client, queued_jobs):
        body = pr_payload()
        sig = make_signature(body)
        base = {
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        }
        r1 = await client.post("/webhook", content=body, headers={**base, "X-GitHub-Delivery": "del-A"})
        r2 = await client.post("/webhook", content=body, headers={**base, "X-GitHub-Delivery": "del-B"})
        assert r1.json()["status"] == "queued"
        assert r2.json()["status"] == "queued"
        assert len(queued_jobs) == 2


# ---------------------------------------------------------------------------
# Gate 3 — Event filtering
# ---------------------------------------------------------------------------

class TestEventFiltering:

    async def test_pull_request_event_is_queued(self, client, queued_jobs):
        body = pr_payload()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-pr-event",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.json()["status"] == "queued"
        assert len(queued_jobs) == 1

    async def test_push_event_is_ignored(self, client, queued_jobs):
        body = json.dumps({"ref": "refs/heads/main", "commits": []}).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-push",
                "X-GitHub-Event": "push",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert resp.json()["event"] == "push"
        assert len(queued_jobs) == 0

    async def test_issues_event_is_ignored(self, client, queued_jobs):
        body = json.dumps({"action": "opened", "issue": {"number": 1}}).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-issue",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert resp.json()["status"] == "ignored"
        assert len(queued_jobs) == 0


# ---------------------------------------------------------------------------
# Gate 4 — Job payload correctness
# ---------------------------------------------------------------------------

class TestJobPayload:

    async def test_queued_job_contains_pr_number(self, client, queued_jobs):
        body = pr_payload(pr_number=99)
        await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-payload-pr",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert queued_jobs[0]["payload"]["pull_request"]["number"] == 99

    async def test_queued_job_contains_repo_name(self, client, queued_jobs):
        body = pr_payload(repo="acme/my-service")
        await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-payload-repo",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert queued_jobs[0]["payload"]["repository"]["full_name"] == "acme/my-service"

    async def test_response_includes_job_id_and_delivery(self, client, queued_jobs):
        body = pr_payload()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": make_signature(body),
                "X-GitHub-Delivery": "delivery-response-check",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        data = resp.json()
        assert "job_id" in data
        assert data["delivery_id"] == "delivery-response-check"
        assert data["job_id"] == "mock-job-1"
