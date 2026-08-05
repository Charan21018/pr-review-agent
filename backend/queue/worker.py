"""
backend/queue/worker.py — ARQ worker definition.

This module defines:
  - review_pr: the ARQ task function (stub for M1; M2 fills it with specialists)
  - WorkerSettings: ARQ worker configuration

Usage (production):
    arq backend.queue.worker.WorkerSettings
"""

from typing import Any


# ---------------------------------------------------------------------------
# ARQ task functions
# ---------------------------------------------------------------------------
async def review_pr(ctx: dict, payload: dict) -> dict:
    """
    Entry point for the async review pipeline.

    M1: stub — validates payload shape and returns immediately.
    M2: will fan out to 4 parallel specialist agents.
    M3: will add RAG retrieval before each specialist call.
    """
    pr_number = payload.get("pull_request", {}).get("number", 0)
    repo = payload.get("repository", {}).get("full_name", "unknown/repo")
    return {"status": "pending", "pr": pr_number, "repo": repo}


# ---------------------------------------------------------------------------
# ARQ worker settings (production)
# ---------------------------------------------------------------------------
class WorkerSettings:
    """ARQ reads this class to configure the worker process."""

    functions = [review_pr]

    # Imported lazily in webhook.py to avoid test-time Redis dependency.
    # Set via REDIS_URL env var; default matches settings.py.
    redis_settings = None  # overridden at startup via arq CLI --redis-url
