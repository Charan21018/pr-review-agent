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
import os
from typing import Callable, Awaitable, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, APIRouter

from backend.settings import settings

# Both app (for tests) and router (for main.py) are defined here
app = FastAPI(title="AI PR Review Agent — Webhook Service")
router = APIRouter()

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
    from backend.queue_enqueuer import enqueue_review_job  # noqa: PLC0415 — intentional lazy import

    payload_bytes = json.dumps(payload).encode("utf-8")
    delivery_id = payload.get("delivery_id", "")
    return await enqueue_review_job(payload_bytes, delivery_id=delivery_id)


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


async def handle_webhook(
    request: Request,
    x_hub_signature_256: Optional[str],
    x_github_delivery: Optional[str],
    x_github_event: Optional[str],
    enqueue_fn: Callable[[dict], Awaitable[str]],
) -> dict:
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
    payload["delivery_id"] = x_github_delivery
    job_id = await enqueue_fn(payload)

    return {"status": "queued", "job_id": str(job_id), "delivery_id": x_github_delivery}


# Register endpoint on both app and router
@app.post("/webhook")
async def app_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    enqueue_fn: Callable[[dict], Awaitable[str]] = Depends(get_enqueue_fn),
) -> dict:
    return await handle_webhook(request, x_hub_signature_256, x_github_delivery, x_github_event, enqueue_fn)


@router.post("/webhook")
async def router_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    enqueue_fn: Callable[[dict], Awaitable[str]] = Depends(get_enqueue_fn),
) -> dict:
    return await handle_webhook(request, x_hub_signature_256, x_github_delivery, x_github_event, enqueue_fn)
