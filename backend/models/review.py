"""backend/models/review.py — PR Review and structured result models."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from backend.models.findings import Finding
from backend.models.enums import ReviewStatus, Outcome


class PRReview(BaseModel):
    """One complete PR review — the output of the full agent pipeline."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    repo: str = Field(..., description="GitHub repo full_name, e.g. 'owner/repo'")
    pr_number: int = Field(..., description="GitHub pull request number")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ReviewStatus = ReviewStatus.PENDING
    findings: List[Finding] = Field(default_factory=list)
    summary: Optional[str] = None
    overall_confidence: Optional[float] = None
    outcome: Optional[Outcome] = None
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def has_critical(self) -> bool:
        """True if any finding is CRITICAL — triggers escalation regardless of confidence."""
        return any(f.is_critical_block() for f in self.findings)


class ReviewSummary(BaseModel):
    """Lightweight summary for list views."""
    id: uuid.UUID
    repo: str
    pr_number: int
    created_at: datetime
    status: ReviewStatus
    outcome: Optional[Outcome] = None
    finding_count: int = 0
    total_cost_usd: float = 0.0
