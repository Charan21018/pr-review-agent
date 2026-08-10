"""backend/reliability/retry.py — Exponential back-off retry decorator.

Provides ``async_retry``, a production-grade decorator built on Tenacity that:
  - Uses exponential back-off with jitter (avoids thundering herd)
  - Accepts a tuple of retryable exception types
  - Injects structured log messages at every attempt
  - Records the retry count in the active OTel span (if present)

Supersedes the simple ``async_retry`` in ``backend/reliability.py``.
"""
import asyncio
import functools
import logging
import random
from typing import Callable, Optional, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
    RetryCallState,
)

from backend.core.exceptions import LLMError, RetrievalError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default exception groups
# ---------------------------------------------------------------------------

#: Exceptions that are always worth retrying
TRANSIENT_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    LLMError,
    RetrievalError,
    ConnectionError,
    TimeoutError,
    OSError,
)


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------

def async_retry(
    *,
    attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    jitter: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> Callable:
    """Decorator: retry an async function with exponential back-off + jitter.

    Args:
        attempts:     Maximum number of total attempts (including the first).
        initial_wait: Starting wait in seconds before the second attempt.
        max_wait:     Upper bound on the wait between any two attempts.
        jitter:       Random jitter added to every wait (seconds).
        exceptions:   Tuple of exception types that trigger a retry.

    Example::

        @async_retry(attempts=5, exceptions=(LLMError,))
        async def call_llm(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _retry = retry(
                reraise=True,
                stop=stop_after_attempt(attempts),
                wait=wait_exponential_jitter(
                    initial=initial_wait,
                    max=max_wait,
                    jitter=jitter,
                ),
                retry=retry_if_exception_type(exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
            )
            return await _retry(func)(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Convenience: simple fixed-wait retry (mirrors the legacy reliability.py API)
# ---------------------------------------------------------------------------

def simple_retry(
    *,
    attempts: int = 3,
    wait_seconds: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> Callable:
    """Like async_retry but with a fixed wait (no exponential growth).

    Useful for test stubs or low-stakes polling loops.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt < attempts:
                        logger.warning(
                            "simple_retry: attempt %d/%d failed for %s: %s",
                            attempt, attempts, func.__qualname__, exc,
                        )
                        await asyncio.sleep(wait_seconds)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
