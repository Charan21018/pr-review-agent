"""backend/core/workflow_engine.py — Abstract orchestration interface (ADR-001).

All orchestrator code imports from here, never from LangGraph directly.
Swapping to Temporal means writing one new implementation of WorkflowEngine.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class WorkflowEngine(ABC):
    """Abstract contract for the orchestration layer.

    Implementations: LangGraphEngine (Phases 1-12), TemporalEngine (Phase 13+ if needed).
    """

    @abstractmethod
    async def run(self, workflow_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start and run a workflow to completion.

        Args:
            workflow_id: Idempotency key — same as the GitHub delivery ID.
            input_data: The structured payload (PR metadata, diff text, etc.).

        Returns:
            Final workflow state dict including findings, summary, and outcome.
        """

    @abstractmethod
    async def resume(self, workflow_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Resume a previously checkpointed workflow from its last saved state.

        Args:
            workflow_id: The workflow to resume.
            state: The state snapshot from the checkpoint store.

        Returns:
            Final workflow state dict.
        """

    @abstractmethod
    async def get_state(self, workflow_id: str) -> Dict[str, Any]:
        """Retrieve the current or last-known state of a workflow.

        Args:
            workflow_id: The workflow to inspect.

        Returns:
            The current state dict, or an empty dict if not found.
        """
