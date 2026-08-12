"""
backend/agents/base.py — Abstract Base Specialist Agent.

Invariant I1: Does NOT import from api/, queue/, or db/.
Invariant I2: Wraps analysis execution in strict timeouts.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import asyncio

from backend.agents.schemas import Finding


class BaseSpecialistAgent(ABC):
    """Base class for all PR review specialist agents."""

    def __init__(self, name: str, timeout_seconds: float = 10.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
        # Set by analyze() as a side effect of its chat_completion_json() call
        # (model, tokens_in, tokens_out, cost_usd, latency_ms). Kept off the
        # analyze()/run_with_timeout() return type so every existing caller
        # that expects a plain List[Finding] is unaffected; the orchestrator
        # reads this after run_with_timeout() to record cost/token events.
        self.last_call_meta: Optional[Dict[str, Any]] = None

    @abstractmethod
    async def analyze(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        """Analyze a diff (optionally using retrieved context chunks) and return findings."""
        pass

    async def run_with_timeout(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> List[Finding]:
        """Execute analyze() with a strict timeout guard (I2 invariant)."""
        try:
            return await asyncio.wait_for(
                self.analyze(pr_diff, context_chunks),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            # Fallback on timeout: return empty findings list gracefully (degrade to slower-but-correct)
            return []
