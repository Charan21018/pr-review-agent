"""
backend/api/hitl_endpoints.py — Human‑in‑the‑loop review API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
import uuid

from backend.db.session import get_db
from backend.db.models import HitlReview, FindingRecord
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/hitl", tags=["hitl"])


class HITLEventCreate(BaseModel):
    decision: Literal["APPROVE", "REJECT"] = Field(..., description="APPROVE (dismiss finding) or REJECT (confirm finding)")
    reviewer: Optional[str] = Field(None, description="Optional reviewer name")
    comments: Optional[str] = Field(None, description="Optional comments")


class HITLClaim(BaseModel):
    reviewer_name: str = Field(..., description="Name of the reviewer claiming this item")


class HITLResolve(BaseModel):
    decision: Literal["APPROVE", "REJECT"] = Field(..., description="APPROVE (dismiss finding) or REJECT (confirm finding)")
    reviewer_name: str = Field(..., description="Name of the resolving reviewer")
    comments: Optional[str] = Field(None, description="Optional comments")


@router.get("/queue", response_model=List[dict])
async def list_pending_reviews(db: AsyncSession = Depends(get_db)):
    """Return unresolved HITL review items (pending or claimed), joined with
    their finding so the frontend gets a human-readable escalation reason and
    the parent review id rather than a bare finding_id."""
    stmt = (
        select(HitlReview, FindingRecord)
        .join(FindingRecord, HitlReview.finding_id == FindingRecord.id)
        .where(HitlReview.status != "completed")
        .order_by(HitlReview.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": str(hitl.id),
            "review_id": str(finding.review_id),
            "escalated_at": hitl.updated_at.isoformat() if hitl.updated_at else None,
            "status": hitl.status,
            "claimed_by": hitl.assigned_to,
            "decision": hitl.decision,
            "reviewer_comments": hitl.reviewer_comments,
            "reason": f"{finding.severity} finding: {finding.description}" if finding.severity else (finding.description or "Escalated for human review"),
        }
        for hitl, finding in rows
    ]


@router.post("/queue/{item_id}/claim")
async def claim_hitl_item(
    item_id: uuid.UUID,
    payload: HITLClaim,
    db: AsyncSession = Depends(get_db)
):
    """Assign a pending HITL item to a reviewer, without resolving it."""
    stmt = (
        update(HitlReview)
        .where(HitlReview.id == item_id, HitlReview.status == "pending")
        .values(assigned_to=payload.reviewer_name, status="claimed")
    )
    try:
        res = await db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="HITL item not found, or already claimed/resolved")
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
    return {"success": True}


@router.post("/queue/{item_id}/resolve")
async def resolve_hitl_item(
    item_id: uuid.UUID,
    payload: HITLResolve,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a pending HITL item with the reviewer's decision."""
    stmt = (
        update(HitlReview)
        .where(HitlReview.id == item_id)
        .values(
            status="completed",
            decision=payload.decision,
            assigned_to=payload.reviewer_name,
            reviewer_comments=payload.comments,
        )
    )
    try:
        res = await db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="HITL item not found")
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
    return {"success": True}


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
