"""backend/observability/audit.py — Append-only audit trail queries.

The audit trail is immutable: rows are only ever INSERT-ed, never UPDATE-d or DELETE-d.
This satisfies the L9 compliance requirement: every decision, escalation, and resolution
must be traceable with a timestamp, actor, and evidence payload.

The table schema is defined in migrations/003_audit_trail.sql (or equivalent).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import json
import os
import logging

logger = logging.getLogger(__name__)


class AuditEntry:
    """Represents a single immutable audit log record."""

    def __init__(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: Optional[Dict[str, Any]] = None,
        review_id: Optional[uuid.UUID] = None,
        ts: Optional[datetime] = None,
    ):
        self.id = uuid.uuid4()
        self.ts = ts or datetime.now(timezone.utc)
        self.actor = actor          # e.g. "system", "github:octocat", "hitl:reviewer"
        self.action = action        # e.g. "review.created", "finding.escalated", "hitl.approved"
        self.resource_type = resource_type  # e.g. "review", "finding", "hitl_item"
        self.resource_id = resource_id      # UUID or GitHub delivery ID
        self.review_id = review_id
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "ts": self.ts.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "review_id": str(self.review_id) if self.review_id else None,
            "payload": self.payload,
        }


class AuditTrail:
    """Append-only audit trail backed by PostgreSQL.

    Falls back to in-memory storage (and warning log) when the DB pool is not
    available, so the service never crashes due to audit infrastructure failure.
    """

    def __init__(self):
        self._fallback: List[AuditEntry] = []
        self._pool: Any = None  # asyncpg.Pool, set via set_pool()

    def set_pool(self, pool: Any) -> None:
        """Inject the asyncpg connection pool (called at startup)."""
        self._pool = pool

    async def append(self, entry: AuditEntry) -> None:
        """Persist an audit entry. Never raises — logs instead."""
        self._fallback.append(entry)

        if self._pool is None:
            logger.warning(
                "AuditTrail: no DB pool available, entry stored in-memory only: %s",
                entry.action,
            )
            return

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_trail (
                        id, ts, actor, action, resource_type, resource_id, review_id, payload
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    entry.id,
                    entry.ts,
                    entry.actor,
                    entry.action,
                    entry.resource_type,
                    entry.resource_id,
                    entry.review_id,
                    json.dumps(entry.payload),
                )
        except Exception as exc:
            logger.error("AuditTrail: failed to persist entry '%s': %s", entry.action, exc)

    async def query(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Read audit entries matching optional filters.

        Returns raw dicts to avoid coupling callers to AuditEntry internals.
        """
        if self._pool is None:
            # Return from in-memory fallback
            results = self._fallback
            if resource_type:
                results = [e for e in results if e.resource_type == resource_type]
            if resource_id:
                results = [e for e in results if e.resource_id == resource_id]
            if actor:
                results = [e for e in results if e.actor == actor]
            return [e.to_dict() for e in results[-limit:]]

        try:
            clauses: List[str] = []
            params: List[Any] = []
            idx = 1
            if resource_type:
                clauses.append(f"resource_type = ${idx}")
                params.append(resource_type)
                idx += 1
            if resource_id:
                clauses.append(f"resource_id = ${idx}")
                params.append(resource_id)
                idx += 1
            if actor:
                clauses.append(f"actor = ${idx}")
                params.append(actor)
                idx += 1

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            params.append(limit)

            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    f"SELECT * FROM audit_trail {where} ORDER BY ts DESC LIMIT ${idx}",
                    *params,
                )
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("AuditTrail: query failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Typed helpers for common audit actions
    # ------------------------------------------------------------------

    async def log_review_created(
        self,
        review_id: uuid.UUID,
        repo: str,
        pr_number: int,
        delivery_id: str,
    ) -> None:
        entry = AuditEntry(
            actor="system",
            action="review.created",
            resource_type="review",
            resource_id=str(review_id),
            review_id=review_id,
            payload={"repo": repo, "pr_number": pr_number, "delivery_id": delivery_id},
        )
        await self.append(entry)

    async def log_finding_escalated(
        self,
        review_id: uuid.UUID,
        finding_summary: str,
        severity: str,
    ) -> None:
        entry = AuditEntry(
            actor="system",
            action="finding.escalated",
            resource_type="finding",
            resource_id=str(review_id),
            review_id=review_id,
            payload={"summary": finding_summary, "severity": severity},
        )
        await self.append(entry)

    async def log_hitl_decision(
        self,
        review_id: uuid.UUID,
        decision: str,
        reviewer: str,
        comment: Optional[str] = None,
    ) -> None:
        entry = AuditEntry(
            actor=f"hitl:{reviewer}",
            action=f"hitl.{decision.lower()}",
            resource_type="hitl_item",
            resource_id=str(review_id),
            review_id=review_id,
            payload={"decision": decision, "comment": comment},
        )
        await self.append(entry)


# Global singleton
audit_trail = AuditTrail()
