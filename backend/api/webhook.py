"""
backend/api/webhook.py — GitHub PR webhook ingress.

Invariants enforced here (context-graph.json):
  I1: this module imports NOTHING from backend.queue at module level
      (import is deferred to _production_enqueue so tests never touch Redis)
  I2: every inbound request is guarded before any side-effect
  I3: cost/latency events are NOT written here — that is observability's job (M4)
"""

import hashlib
import hmac
import json
from typing import Callable, Awaitable, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from backend.settings import settings

app = FastAPI(title="AI PR Review Agent — Webhook Service")

# ---------------------------------------------------------------------------
# Dedup store
# In-memory for M1; upgraded to Redis SET with TTL in M4 (observability).
# Acceptable for M1: a process restart resets it, but GitHub's retry window
# is short and a duplicate job is idempotent at the specialist level (M2).
# ---------------------------------------------------------------------------
_seen_deliveries: set[str] = set()


# ---------------------------------------------------------------------------
# Queue dependency — injectable for testing
# ---------------------------------------------------------------------------
async def _production_enqueue(payload: dict) -> str:
    """Enqueue a review job via ARQ + Redis. Imported lazily: never executed in tests."""
    from arq import create_pool  # noqa: PLC0415 — intentional lazy import
    from arq.connections import RedisSettings  # noqa: PLC0415

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    job = await pool.enqueue_job("review_pr", payload)
    await pool.aclose()
    return job.job_id


def get_enqueue_fn() -> Callable[[dict], Awaitable[str]]:
    """FastAPI dependency: returns the enqueue callable.

    Tests override this via app.dependency_overrides[get_enqueue_fn] = ...
    """
    return _production_enqueue


# ---------------------------------------------------------------------------
# Signature verification (I2: guard before any side-effect)
# ---------------------------------------------------------------------------
def _verify_signature(body: bytes, signature: str) -> bool:
    """Constant-time comparison of GitHub's HMAC-SHA256 webhook signature."""
    secret = settings.github_webhook_secret.encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------
@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    enqueue_fn: Callable[[dict], Awaitable[str]] = Depends(get_enqueue_fn),
) -> dict:
    """
    Receive a GitHub webhook, verify it, deduplicate it, and enqueue a review job.

    Gates (in order — fail fast, side-effect nothing before all gates pass):
      1. Signature present and valid  → 401 if not
      2. Delivery ID not seen before  → 200 "duplicate" if already processed
      3. Event is pull_request        → 200 "ignored" for other event types
      4. Enqueue job                  → 200 "queued" with job_id
    """
    body = await request.body()

    # Gate 1 — HMAC signature (I2: every inbound path has a trust guard)
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")
    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Gate 2 — Idempotency (deduplicate retried GitHub deliveries)
    if x_github_delivery:
        if x_github_delivery in _seen_deliveries:
            return {"status": "duplicate", "delivery_id": x_github_delivery}
        _seen_deliveries.add(x_github_delivery)

    # Gate 3 — Event filter (only process pull_request events in M1)
    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    # Gate 4 — Enqueue for async processing by specialist agents (M2)
    payload: dict = json.loads(body) if body else {}
    job_id = await enqueue_fn(payload)

    return {"status": "queued", "job_id": str(job_id), "delivery_id": x_github_delivery}
