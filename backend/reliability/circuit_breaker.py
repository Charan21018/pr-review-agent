"""backend/reliability/circuit_breaker.py — Circuit breaker pattern.

A circuit breaker prevents cascading failures by halting calls to a
dependency that is repeatedly failing:

  CLOSED  → normal; calls pass through
  OPEN    → dependency is failing; calls short-circuit with CircuitOpenError
  HALF_OPEN → probing; one test call is allowed through to check recovery

Configuration is per-breaker-name so each downstream service (LLM provider,
TigerDB, GitHub API) can have independent thresholds.

All state is in-process (not distributed).  For multi-instance deployments,
back the state with Redis — the structure is ready for that extension.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from backend.core.exceptions import CircuitOpenError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # consecutive failures before opening
    success_threshold: int = 2      # consecutive successes in HALF_OPEN to close
    timeout_seconds: float = 30.0   # time to stay OPEN before probing


@dataclass
class _CircuitState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: Optional[float] = None


class CircuitBreaker:
    """Named circuit breaker.

    Usage::

        breaker = CircuitBreaker("gemini", config=CircuitBreakerConfig(failure_threshold=3))

        @breaker.protect
        async def call_gemini(prompt: str) -> str:
            ...
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = _CircuitState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state.state

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute *func* through the breaker — raises CircuitOpenError if open."""
        async with self._lock:
            await self._check_state()

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                await self._on_success()
            return result
        except Exception as exc:
            async with self._lock:
                await self._on_failure()
            raise

    def protect(self, func: Callable) -> Callable:
        """Decorator form of :meth:`call`."""
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        return wrapper

    # ------------------------------------------------------------------
    # Internal state machine transitions
    # ------------------------------------------------------------------

    async def _check_state(self) -> None:
        st = self._state
        if st.state == CircuitState.OPEN:
            elapsed = time.monotonic() - (st.opened_at or 0)
            if elapsed >= self.config.timeout_seconds:
                logger.info("CircuitBreaker[%s]: OPEN → HALF_OPEN", self.name)
                st.state = CircuitState.HALF_OPEN
                st.success_count = 0
            else:
                remaining = self.config.timeout_seconds - elapsed
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN for {remaining:.1f}s more."
                )
        # HALF_OPEN: allow the call through (one probe at a time)

    async def _on_success(self) -> None:
        st = self._state
        if st.state == CircuitState.HALF_OPEN:
            st.success_count += 1
            if st.success_count >= self.config.success_threshold:
                logger.info("CircuitBreaker[%s]: HALF_OPEN → CLOSED", self.name)
                st.state = CircuitState.CLOSED
                st.failure_count = 0
                st.success_count = 0
        elif st.state == CircuitState.CLOSED:
            st.failure_count = 0  # reset on any success

    async def _on_failure(self) -> None:
        st = self._state
        st.failure_count += 1
        if st.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
            if st.failure_count >= self.config.failure_threshold:
                logger.warning(
                    "CircuitBreaker[%s]: → OPEN after %d failures",
                    self.name, st.failure_count,
                )
                st.state = CircuitState.OPEN
                st.opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED (useful for tests)."""
        self._state = _CircuitState()


# ---------------------------------------------------------------------------
# Global registry of named breakers
# ---------------------------------------------------------------------------

class CircuitBreakerRegistry:
    """Central registry so breakers can be shared across modules."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def all_states(self) -> Dict[str, str]:
        return {name: b.state.value for name, b in self._breakers.items()}


registry = CircuitBreakerRegistry()

# Pre-register breakers for known external dependencies
registry.get("gemini", CircuitBreakerConfig(failure_threshold=5, timeout_seconds=60))
registry.get("anthropic", CircuitBreakerConfig(failure_threshold=5, timeout_seconds=60))
registry.get("tigerdb", CircuitBreakerConfig(failure_threshold=3, timeout_seconds=30))
registry.get("github_api", CircuitBreakerConfig(failure_threshold=3, timeout_seconds=30))
