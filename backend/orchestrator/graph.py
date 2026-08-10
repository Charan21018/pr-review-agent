from langgraph.graph import StateGraph, END

from backend.orchestrator.state import ReviewState
from backend.orchestrator.nodes import (
    retrieve_context_node,
    run_specialists_node,
    aggregate_findings_node,
    hitl_gate_node,
    post_results_node,
)


def create_review_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(ReviewState)

    # 1. Add all nodes
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("run_specialists", run_specialists_node)
    workflow.add_node("aggregate_findings", aggregate_findings_node)
    workflow.add_node("hitl_gate", hitl_gate_node)
    workflow.add_node("post_results", post_results_node)

    # 2. Add edges (Linear execution flow)
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "run_specialists")
    workflow.add_edge("run_specialists", "aggregate_findings")
    workflow.add_edge("aggregate_findings", "hitl_gate")
    workflow.add_edge("hitl_gate", "post_results")
    workflow.add_edge("post_results", END)

    # 3. Compile
    return workflow.compile()
