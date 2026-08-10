"""
backend/api/hitl.py — HITL decision helper function and test endpoints.

Handles both SQLite (for local testing/integration) and Postgres/SQLAlchemy (for production).
"""
import uuid
import time
import asyncio
import sqlite3
import os
from typing import Dict, Any
from fastapi import APIRouter

router = APIRouter()

@router.post("/hitl")
async def hitl_decision_endpoint(payload: dict):
    db_path = os.getenv("DATABASE_URL", "database.db")
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO hitl_events (review_id, decision, reviewer, comments) VALUES (?, ?, ?, ?)",
            (payload["review_id"], payload["decision"], payload["reviewer"], payload["comments"])
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "recorded"}

async def await_decision(review_id: str, timeout: int = 30) -> Dict[str, Any]:
    """Poll hitl_events or hitl_reviews for a decision on the review_id."""
    db_path = os.getenv("DATABASE_URL", "database.db")
    start = time.time()
    
    while time.time() - start < timeout:
        # Check SQLite
        if os.path.exists(db_path) or "test.db" in db_path:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hitl_events'")
                if cursor.fetchone():
                    cursor.execute(
                        "SELECT decision, reviewer, comments FROM hitl_events WHERE review_id = ? ORDER BY created_at DESC LIMIT 1",
                        (review_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return {
                            "decision": row[0],
                            "reviewer": row[1],
                            "comments": row[2],
                        }
            except Exception as e:
                print(f"[Warning] SQLite poll failed: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()

        # Check Postgres/SQLAlchemy
        tiger_db = os.getenv("TIGER_DATABASE_URL")
        if tiger_db:
            try:
                from backend.db.session import get_db
                from backend.db.models import FindingRecord, HitlReview
                from sqlalchemy import select
                async with get_db() as db:
                    review_uuid = uuid.UUID(review_id)
                    stmt = select(FindingRecord.id).where(FindingRecord.review_id == review_uuid)
                    res = await db.execute(stmt)
                    finding_ids = res.scalars().all()
                    if finding_ids:
                        stmt_hitl = select(HitlReview).where(HitlReview.finding_id.in_(finding_ids))
                        res_hitl = await db.execute(stmt_hitl)
                        reviews = res_hitl.scalars().all()
                        if reviews and all(r.status == "completed" for r in reviews):
                            any_rejected = any(r.decision == "REJECT" for r in reviews)
                            decision = "REQUEST_CHANGES" if any_rejected else "APPROVE"
                            comments = "; ".join(r.reviewer_comments for r in reviews if r.reviewer_comments)
                            reviewer = reviews[0].assigned_to or "human"
                            return {
                                "decision": decision,
                                "reviewer": reviewer,
                                "comments": comments,
                            }
            except Exception as e:
                print(f"[Warning] Postgres poll failed: {e}")

        await asyncio.sleep(1)

    raise TimeoutError(f"No HITL decision recorded for review_id {review_id} within {timeout}s")
