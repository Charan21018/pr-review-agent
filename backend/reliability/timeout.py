"""backend/reliability/timeout.py — Async timeout wrapper.

Provides a clean decorator and context manager for enforcing hard deadlines
on async operations.  Raises ``asyncio.TimeoutError`` (not a custom type)
so callers can catch it generically.

Also provides ``with_timeout``, a lower-level helper for ad-hoc use.

Usage::

    @timeout(seconds=30, label="llm_call")
    async def call_llm(prompt: str) -> str:
        ...

    # Or inline:
    result = await with_timeout(some_coro(), seconds=10, label="db_query")
"""
import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_timeout(
    coro: Coroutine[Any, Any, T],
    *,
    seconds: float,
    label: str = "operation",
) -> T:
    """Await *coro* with a hard deadline.

    Logs a warning on timeout before re-raising ``asyncio.TimeoutError``.

    Args:
        coro:    The coroutine to execute.
        seconds: Maximum allowed wall-clock time.
        label:   Human-readable name for log messages.

    Raises:
        asyncio.TimeoutError: If the deadline is exceeded.
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        logger.warning("Timeout: '%s' exceeded %.1fs deadline", label, seconds)
        raise


def timeout(
    seconds: float,
    label: Optional[str] = None,
) -> Callable:
    """Decorator that applies a hard deadline to an async function.

    Args:
        seconds: Maximum execution time in seconds.
        label:   Human-readable name (defaults to ``func.__qualname__``).

    Example::

        @timeout(seconds=60, label="github_fetch")
        async def fetch_diff(repo: str, pr: int) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        _label = label or func.__qualname__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(
                func(*args, **kwargs),
                seconds=seconds,
                label=_label,
            )

        return wrapper

    return decorator


class DeadlineScope:
    """Async context manager that propagates a deadline across multiple awaits.

    Each individual call still needs to respect the remaining budget.
    This is a best-effort helper; it does NOT cancel sub-tasks automatically.

    Usage::

        async with DeadlineScope(total_seconds=120) as dl:
            result1 = await with_timeout(coro1(), seconds=dl.remaining, label="step1")
            result2 = await with_timeout(coro2(), seconds=dl.remaining, label="step2")
    """

    def __init__(self, total_seconds: float):
        self._total = total_seconds
        self._start: float = 0.0

    async def __aenter__(self) -> "DeadlineScope":
        import time
        self._start = time.monotonic()
        return self

    async def __aexit__(self, *exc_info):
        pass

    @property
    def remaining(self) -> float:
        import time
        elapsed = time.monotonic() - self._start
        return max(0.0, self._total - elapsed)

    @property
    def expired(self) -> bool:
        return self.remaining <= 0.0
