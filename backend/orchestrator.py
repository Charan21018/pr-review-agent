"""
orchestrator.py – Enqueues PR review jobs into Redis via ARQ.

On Windows + Python 3.14, redis.asyncio's async socket connect is broken
due to ProactorEventLoop / SelectorEventLoop CancelledError bugs.  We work
around this by running all Redis I/O in a background thread
(asyncio.to_thread) so the synchronous redis.Redis client is used.

The job is serialised with ARQ's own serialize_job() so that ARQ workers
can pick it up without any modifications.
"""
import os
import json
import asyncio
import threading
import time
from typing import Any, Dict, Optional
from uuid import uuid4

import redis as sync_redis

# ARQ internals we reuse to stay 100% wire-compatible
from arq.jobs import serialize_job
from arq.utils import timestamp_ms

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ARQ_QUEUE   = "arq:queue"
JOB_PREFIX  = "arq:job:"

# Default expiry: 25 hours in milliseconds (same as ARQ default)
EXPIRES_EXTRA_MS = 86_400_000 + 3_600_000

# ── Singleton sync Redis client ───────────────────────────────────────────────
_client: Optional[sync_redis.Redis] = None
_lock = threading.Lock()


def _get_client() -> sync_redis.Redis:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = sync_redis.Redis.from_url(
                    REDIS_URL, socket_connect_timeout=5, socket_timeout=5
                )
    return _client


def _ping_sync() -> bool:
    return _get_client().ping()


def _enqueue_sync(function_name: str, job_id: str, payload: dict) -> str:
    """Enqueue an ARQ job using the sync Redis client and ARQ's wire format."""
    r = _get_client()
    job_key = f"{JOB_PREFIX}{job_id}"

    enqueue_time_ms = timestamp_ms()
    score = enqueue_time_ms
    expires_ms = EXPIRES_EXTRA_MS

    # Serialise with ARQ's own function so workers can deserialise it
    job_bytes = serialize_job(
        function_name,
        args=(),
        kwargs={"payload": payload},
        job_try=None,
        enqueue_time_ms=enqueue_time_ms,
        serializer=None,  # use default (msgpack)
    )

    pipe = r.pipeline(transaction=True)
    # Skip if job already exists (idempotency)
    if r.exists(job_key):
        return job_id

    pipe.psetex(job_key, expires_ms, job_bytes)
    pipe.zadd(ARQ_QUEUE, {job_id: score})
    pipe.execute()
    return job_id


# ── Public API ────────────────────────────────────────────────────────────────

async def init_pool() -> None:
    """Validate Redis connectivity at startup (non-blocking)."""
    ok = await asyncio.to_thread(_ping_sync)
    if not ok:
        raise RuntimeError("Redis ping failed at startup")
    print("ARQ orchestrator: Redis connection OK")


async def close_pool() -> None:
    """Close the sync Redis connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def enqueue_review_job(payload_bytes: bytes, delivery_id: str) -> str:
    """Enqueue a PR review job.

    Args:
        payload_bytes: The raw request body received from GitHub.
        delivery_id: The ``X-GitHub-Delivery`` header value – used as a unique
            job identifier to guarantee idempotency.

    Returns:
        The job ID string.
    """
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON payload: {exc}")

    job_id = await asyncio.to_thread(_enqueue_sync, "review_pr", delivery_id, payload)
    return job_id
