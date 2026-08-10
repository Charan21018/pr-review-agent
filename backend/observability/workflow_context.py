"""backend/observability/workflow_context.py — ContextVar for review_id.

Stores the active ``review_id`` in an async-safe ContextVar so that any
coroutine in the call-stack can retrieve it without threading parameters
through every function signature.

Usage::

    from backend.observability.workflow_context import set_review_id, get_review_id

    # At the start of a review job:
    token = set_review_id(some_uuid)
    try:
        await run_pipeline(...)
    finally:
        reset_review_id(token)

The JSON log formatter (observability/logging.py) reads this ContextVar
automatically and injects ``review_id`` into every log line emitted during
the review job.
"""
import uuid
from contextvars import ContextVar
from typing import Optional, Token

# ContextVar is the recommended async-safe way to store per-request state.
# Each asyncio Task gets its own copy — no cross-task contamination.
_review_id_var: ContextVar[Optional[uuid.UUID]] = ContextVar(
    "review_id", default=None
)


def set_review_id(review_id: uuid.UUID) -> Token:
    """Set the current review ID; returns a reset token for cleanup."""
    return _review_id_var.set(review_id)


def get_review_id() -> Optional[uuid.UUID]:
    """Return the active review ID, or None if not set."""
    return _review_id_var.get()


def reset_review_id(token: Token) -> None:
    """Reset the ContextVar to its previous value using the token."""
    _review_id_var.reset(token)


class ReviewContext:
    """Async context manager for scoped review_id injection.

    Usage::

        async with ReviewContext(review_id):
            await run_pipeline()
    """

    def __init__(self, review_id: uuid.UUID):
        self._review_id = review_id
        self._token: Optional[Token] = None

    async def __aenter__(self):
        self._token = set_review_id(self._review_id)
        return self

    async def __aexit__(self, *exc_info):
        if self._token is not None:
            reset_review_id(self._token)
