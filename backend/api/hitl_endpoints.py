"""
backend/api/hitl_endpoints.py — Human‑in‑the‑loop review API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
import uuid

from backend.db.session import get_db
from backend.db.models import HitlReview
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/hitl", tags=["hitl"])


class HITLEventCreate(BaseModel):
    decision: Literal["APPROVE", "REJECT"] = Field(..., description="APPROVE (dismiss finding) or REJECT (confirm finding)")
    reviewer: Optional[str] = Field(None, description="Optional reviewer name")
    comments: Optional[str] = Field(None, description="Optional comments")


@router.get("/queue", response_model=List[dict])
async def list_pending_reviews(db: AsyncSession = Depends(get_db)):
    """Return pending HITL review items from the queue."""
    stmt = select(HitlReview).where(HitlReview.status == "pending")
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "finding_id": str(row.finding_id),
            "assigned_to": row.assigned_to,
            "status": row.status,
            "decision": row.decision,
            "reviewer_comments": row.reviewer_comments,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.post("/review/{review_id}")
async def update_review_status(
    review_id: uuid.UUID,
    payload: HITLEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update the status/decision of a pending HITL review by its record ID."""
    stmt = (
        update(HitlReview)
        .where(HitlReview.id == review_id)
        .values(
            status="completed",
            decision=payload.decision,
            assigned_to=payload.reviewer,
            reviewer_comments=payload.comments,
        )
    )
    try:
        res = await db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="HITL review not found")
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
    return {"status": "updated", "review_id": str(review_id)}
