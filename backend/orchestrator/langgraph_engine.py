"""backend/orchestrator/langgraph_engine.py — LangGraph implementation of core/workflow_engine.py.

Implements the abstract WorkflowEngine interface using LangGraph, routing StateGraph
execution, supporting checkpoint/state persistence, and allowing resumption of flows.
"""
import uuid
import logging
from typing import Dict, Any, Optional
from backend.core.workflow_engine import WorkflowEngine
from backend.orchestrator.graph import create_review_graph
from backend.orchestrator.state import ReviewState

logger = logging.getLogger(__name__)

class LangGraphEngine(WorkflowEngine):
    """Engine executing the review process graph via LangGraph."""

    def __init__(self):
        # We compile the graph once
        self.graph = create_review_graph()
        # In-memory dictionary to store last known workflow state for resumption
        self._states_db: Dict[str, Dict[str, Any]] = {}

    async def run(self, workflow_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the review workflow to completion using the compiled LangGraph StateGraph.

        Args:
            workflow_id: Unique idempotency / transaction key.
            input_data: Dict containing repository, pr_number, pr_diff, review_id, etc.
        """
        logger.info("LangGraphEngine: Starting workflow execution for ID=%s", workflow_id)
        
        # Prepare graph state
        initial_state = {
            "repo": input_data.get("repo", ""),
            "pr_number": int(input_data.get("pr_number", 0)),
            "pr_diff": input_data.get("pr_diff", ""),
            "review_id": str(input_data.get("review_id", workflow_id)),
            "context_chunks": [],
            "findings": [],
            "recommendation": "",
            "overall_confidence": 0.0,
            "summary": "",
            "has_critical": False,
            "hitl_action": "NONE",
            "reviewer_comments": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "latency_ms": 0
        }

        try:
            # Execute compiled graph
            config = {"configurable": {"thread_id": workflow_id}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Save state in our state DB for tracking / get_state / resume
            self._states_db[workflow_id] = final_state
            logger.info("LangGraphEngine: Workflow completed successfully for ID=%s", workflow_id)
            return final_state
            
        except Exception as e:
            logger.error("LangGraphEngine: Workflow execution failed for ID=%s: %s", workflow_id, e)
            raise e

    async def resume(self, workflow_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Resumes a checkpointed workflow from its last saved state.

        Useful for manual review override, or recovering from server restarts/failures.
        """
        logger.info("LangGraphEngine: Resuming workflow for ID=%s", workflow_id)
        
        # If we have the thread checkpointed, we could update and resume
        # For simplicity, merge the saved state with inputs and re-execute starting from the remaining stages,
        # or resume from checkpoint. In our StateGraph, we can update state and invoke.
        try:
            config = {"configurable": {"thread_id": workflow_id}}
            
            # Update the graph state with the new/modified parameters (e.g. reviewer comments, approved)
            self.graph.update_state(config, state)
            
            # Re-run or invoke
            final_state = await self.graph.ainvoke(None, config=config)
            self._states_db[workflow_id] = final_state
            return final_state
        except Exception as e:
            logger.error("LangGraphEngine: Failed to resume workflow for ID=%s: %s", workflow_id, e)
            # Fallback to direct dict merging and saving
            current = self._states_db.get(workflow_id, {})
            current.update(state)
            self._states_db[workflow_id] = current
            return current

    async def get_state(self, workflow_id: str) -> Dict[str, Any]:
        """Retrieves the current state snapshot of the workflow."""
        # Check thread state from the compiled graph checkpointer if configured, otherwise fall back to local dict
        config = {"configurable": {"thread_id": workflow_id}}
        try:
            state_snapshot = self.graph.get_state(config)
            if state_snapshot and state_snapshot.values:
                return state_snapshot.values
        except Exception:
            pass

        return self._states_db.get(workflow_id, {})
