"""backend/hitl/feedback.py — Feedback capture for the AI PR Review Agent.

Allows developers or reviewers to submit feedback on specific findings,
e.g. true positives, false positives, or recommendations for improvement.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FindingFeedback(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    finding_index: int  # index of the finding in the review list
    feedback_type: str  # "true_positive", "false_positive", "unhelpful", "custom"
    comments: Optional[str] = None
    created_at: datetime
    submitted_by: str

class FeedbackStore:
    """Stores reviewer feedback on specific findings."""

    def __init__(self):
        self._feedbacks: Dict[uuid.UUID, FindingFeedback] = {}
        self._pool: Optional[Any] = None

    def set_pool(self, pool: Any) -> None:
        self._pool = pool

    async def submit_feedback(
        self, review_id: uuid.UUID, finding_index: int, feedback_type: str, submitted_by: str, comments: Optional[str] = None
    ) -> FindingFeedback:
        """Saves a feedback entry."""
        fb = FindingFeedback(
            id=uuid.uuid4(),
            review_id=review_id,
            finding_index=finding_index,
            feedback_type=feedback_type,
            comments=comments,
            created_at=datetime.now(timezone.utc),
            submitted_by=submitted_by
        )
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO finding_feedback (id, review_id, finding_index, feedback_type, comments, created_at, submitted_by)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        fb.id, fb.review_id, fb.finding_index, fb.feedback_type, fb.comments, fb.created_at, fb.submitted_by
                    )
            except Exception as e:
                logger.error("FeedbackStore: Failed to persist feedback: %s", e)

        self._feedbacks[fb.id] = fb
        logger.info("FeedbackStore: Feedback saved for review %s, finding %d", review_id, finding_index)
        return fb

    async def list_feedback_for_review(self, review_id: uuid.UUID) -> List[FindingFeedback]:
        """Lists all feedback received for a given review."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM finding_feedback WHERE review_id = $1", review_id
                    )
                    return [
                        FindingFeedback(
                            id=row["id"],
                            review_id=row["review_id"],
                            finding_index=row["finding_index"],
                            feedback_type=row["feedback_type"],
                            comments=row["comments"],
                            created_at=row["created_at"],
                            submitted_by=row["submitted_by"]
                        )
                        for row in rows
                    ]
            except Exception as e:
                logger.error("FeedbackStore: Failed to list feedback: %s", e)

        return [fb for fb in self._feedbacks.values() if fb.review_id == review_id]

# Global singleton
feedback_store = FeedbackStore()
