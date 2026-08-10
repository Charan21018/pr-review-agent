"""backend/hitl/queue.py — Human-in-the-loop (HITL) review queue.

Allows reviewers to inspect, claim, approve, or reject findings that
escalated due to low confidence or critical security warnings.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.models.enums import ReviewStatus, HitlDecision

logger = logging.getLogger(__name__)

class HitlQueueItem(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    escalated_at: datetime
    status: str  # "pending", "claimed", "resolved"
    claimed_by: Optional[str] = None
    resolved_at: Optional[str] = None
    decision: Optional[HitlDecision] = None
    reviewer_comments: Optional[str] = None
    reason: str  # e.g., "low_confidence", "critical_severity"

class HitlQueue:
    """Queue of items requiring human authorization."""

    def __init__(self):
        self._items: Dict[uuid.UUID, HitlQueueItem] = {}
        self._pool: Optional[Any] = None

    def set_pool(self, pool: Any) -> None:
        self._pool = pool

    async def enqueue(self, review_id: uuid.UUID, reason: str) -> HitlQueueItem:
        """Add a review task to the HITL queue."""
        item = HitlQueueItem(
            id=uuid.uuid4(),
            review_id=review_id,
            escalated_at=datetime.now(timezone.utc),
            status="pending",
            reason=reason
        )
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO hitl_queue (id, review_id, escalated_at, status, reason)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        item.id, item.review_id, item.escalated_at, item.status, item.reason
                    )
            except Exception as e:
                logger.error("HitlQueue: Failed to insert to DB: %s", e)

        self._items[item.id] = item
        logger.info("HitlQueue: Enqueued review %s for reason: %s", review_id, reason)
        return item

    async def list_pending(self) -> List[HitlQueueItem]:
        """List all pending/claimed HITL queue items."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM hitl_queue WHERE status != 'resolved'")
                    return [
                        HitlQueueItem(
                            id=row["id"],
                            review_id=row["review_id"],
                            escalated_at=row["escalated_at"],
                            status=row["status"],
                            claimed_by=row["claimed_by"],
                            resolved_at=row["resolved_at"].isoformat() if row["resolved_at"] else None,
                            decision=HitlDecision(row["decision"]) if row["decision"] else None,
                            reviewer_comments=row["reviewer_comments"],
                            reason=row["reason"]
                        )
                        for row in rows
                    ]
            except Exception as e:
                logger.error("HitlQueue: DB error listing pending items: %s", e)

        return [item for item in self._items.values() if item.status != "resolved"]

    async def claim_item(self, item_id: uuid.UUID, reviewer_name: str) -> bool:
        """Claim a pending item in the HITL queue."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    res = await conn.execute(
                        "UPDATE hitl_queue SET status = 'claimed', claimed_by = $1 WHERE id = $2 AND status = 'pending'",
                        reviewer_name, item_id
                    )
                    # res format is "UPDATE 1" or similar
                    if "UPDATE 1" in res or "1" in res:
                        return True
            except Exception as e:
                logger.error("HitlQueue: DB error claiming item: %s", e)

        item = self._items.get(item_id)
        if item and item.status == "pending":
            item.status = "claimed"
            item.claimed_by = reviewer_name
            return True
        return False

    async def resolve_item(
        self, item_id: uuid.UUID, decision: HitlDecision, reviewer_name: str, comments: Optional[str] = None
    ) -> Optional[HitlQueueItem]:
        """Resolve a HITL queue item with an approve/reject decision."""
        now = datetime.now(timezone.utc)
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE hitl_queue 
                        SET status = 'resolved', decision = $1, reviewer_comments = $2, resolved_at = $3, claimed_by = $4
                        WHERE id = $5
                        """,
                        decision.value, comments, now, reviewer_name, item_id
                    )
            except Exception as e:
                logger.error("HitlQueue: DB error resolving item: %s", e)

        item = self._items.get(item_id)
        if item:
            item.status = "resolved"
            item.decision = decision
            item.reviewer_comments = comments
            item.resolved_at = now.isoformat()
            item.claimed_by = reviewer_name
            
            # Log the decision to audit trail
            from backend.observability.audit import audit_trail
            await audit_trail.log_hitl_decision(
                review_id=item.review_id,
                decision=decision.value,
                reviewer=reviewer_name,
                comment=comments
            )
            return item
        return None

# Global singleton queue
hitl_queue = HitlQueue()
