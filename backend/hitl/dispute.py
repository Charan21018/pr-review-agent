"""backend/hitl/dispute.py — Developer dispute API / management.

Allows developers to challenge automated agent review findings.
Challenges are routed to a human reviewer queue for manual arbitration.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FindingDispute(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    finding_index: int
    reason: str
    status: str  # "open", "resolved", "dismissed"
    created_at: datetime
    updated_at: Optional[datetime] = None
    developer_name: str
    reviewer_decision: Optional[str] = None
    reviewer_comments: Optional[str] = None

class DisputeStore:
    """Manages dispute entries created by developers."""

    def __init__(self):
        self._disputes: Dict[uuid.UUID, FindingDispute] = {}
        self._pool: Optional[Any] = None

    def set_pool(self, pool: Any) -> None:
        self._pool = pool

    async def create_dispute(
        self, review_id: uuid.UUID, finding_index: int, developer_name: str, reason: str
    ) -> FindingDispute:
        """Create a new dispute entry."""
        dispute = FindingDispute(
            id=uuid.uuid4(),
            review_id=review_id,
            finding_index=finding_index,
            reason=reason,
            status="open",
            created_at=datetime.now(timezone.utc),
            developer_name=developer_name
        )

        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO finding_disputes (id, review_id, finding_index, reason, status, created_at, developer_name)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        dispute.id, dispute.review_id, dispute.finding_index, dispute.reason, dispute.status, dispute.created_at, dispute.developer_name
                    )
            except Exception as e:
                logger.error("DisputeStore: Failed to persist dispute: %s", e)

        self._disputes[dispute.id] = dispute
        logger.info("DisputeStore: Dispute created for review %s, finding %d", review_id, finding_index)
        return dispute

    async def resolve_dispute(
        self, dispute_id: uuid.UUID, decision: str, comments: Optional[str] = None
    ) -> Optional[FindingDispute]:
        """Resolves an open developer dispute."""
        now = datetime.now(timezone.utc)
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE finding_disputes 
                        SET status = 'resolved', reviewer_decision = $1, reviewer_comments = $2, updated_at = $3
                        WHERE id = $4
                        """,
                        decision, comments, now, dispute_id
                    )
            except Exception as e:
                logger.error("DisputeStore: Failed to resolve dispute in DB: %s", e)

        dispute = self._disputes.get(dispute_id)
        if dispute:
            dispute.status = "resolved"
            dispute.reviewer_decision = decision
            dispute.reviewer_comments = comments
            dispute.updated_at = now
            return dispute
        return None

    async def list_open_disputes(self) -> List[FindingDispute]:
        """List all currently open disputes."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM finding_disputes WHERE status = 'open'")
                    return [
                        FindingDispute(
                            id=row["id"],
                            review_id=row["review_id"],
                            finding_index=row["finding_index"],
                            reason=row["reason"],
                            status=row["status"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            developer_name=row["developer_name"],
                            reviewer_decision=row["reviewer_decision"],
                            reviewer_comments=row["reviewer_comments"]
                        )
                        for row in rows
                    ]
            except Exception as e:
                logger.error("DisputeStore: Failed to list open disputes: %s", e)

        return [d for d in self._disputes.values() if d.status == "open"]

# Global singleton
dispute_store = DisputeStore()
