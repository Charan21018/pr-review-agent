"""
backend/api/reviews_endpoints.py — API endpoints for listing PR reviews and findings.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import uuid
import os
import asyncpg

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _get_db_conn() -> asyncpg.Connection:
    url = os.getenv("TIGER_DATABASE_URL", "")
    if "ssl=" in url:
        import urllib.parse as up
        parts = list(up.urlparse(url))
        q = dict(up.parse_qsl(parts[4]))
        q.pop("ssl", None)
        parts[4] = up.urlencode(q)
        url = up.urlunparse(parts)
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url, ssl=True)


@router.get("", response_model=List[Dict[str, Any]])
async def list_reviews():
    """List completed and pending PR review records."""
    conn = await _get_db_conn()
    try:
        sql = """
        SELECT id::text, repo, pr_number, created_at, status, summary, total_cost_usd, total_tokens
        FROM pr_review_records
        ORDER BY created_at DESC;
        """
        rows = await conn.fetch(sql)
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Error] Failed to fetch review records: {e}")
        return []
    finally:
        await conn.close()


@router.get("/{review_id}/findings", response_model=List[Dict[str, Any]])
async def get_findings(review_id: uuid.UUID):
    """Retrieve all findings for a given PR review."""
    conn = await _get_db_conn()
    try:
        sql = """
        SELECT id::text, review_id::text, file_path, line_start, line_end, symbol, severity, description, confidence, created_at
        FROM finding_records
        WHERE review_id = $1
        ORDER BY severity DESC, file_path;
        """
        rows = await conn.fetch(sql, review_id)
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Error] Failed to fetch findings: {e}")
        return []
    finally:
        await conn.close()
