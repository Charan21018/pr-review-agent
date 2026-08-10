"""backend/core/exceptions.py — Shared exception types (ADR-002: inward-only deps)."""


class ReviewAgentError(Exception):
    """Base exception for all review agent errors."""


class BudgetExceededError(ReviewAgentError):
    """Raised when daily token budget cap is exceeded."""


class OrchestrationDeadlockError(ReviewAgentError):
    """Raised when the orchestrator graph deadlocks or times out."""


class RetrievalError(ReviewAgentError):
    """Raised when the memory retrieval layer fails."""


class LLMError(ReviewAgentError):
    """Raised when an LLM call fails after all retries."""


class IdempotencyConflictError(ReviewAgentError):
    """Raised when a duplicate job ID is detected at ingress."""


class SignatureVerificationError(ReviewAgentError):
    """Raised when a webhook HMAC signature is invalid."""


class CircuitOpenError(ReviewAgentError):
    """Raised when a circuit breaker is in the open state."""


class ToolPermissionError(ReviewAgentError):
    """Raised when a tool call exceeds its capability scope."""


class HitlTimeoutError(ReviewAgentError):
    """Raised when no HITL decision arrives within the timeout window."""
