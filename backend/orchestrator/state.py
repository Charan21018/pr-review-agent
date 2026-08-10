from typing import TypedDict, List, Optional, Any

class ReviewState(TypedDict):
    """The state schema for the LangGraph PR review flow."""
    repo: str
    pr_number: int
    pr_diff: str
    review_id: str
    
    # Grounding context retrieved from pgvector
    context_chunks: List[str]
    
    # Findings gathered from specialist agents
    findings: List[Any]
    
    # Aggregation & Decision
    recommendation: str
    overall_confidence: float
    summary: str
    has_critical: bool
    
    # HITL gate state
    hitl_action: str  # NONE, PENDING, APPROVED, REJECTED
    reviewer_comments: Optional[str]
    
    # Metrics
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
