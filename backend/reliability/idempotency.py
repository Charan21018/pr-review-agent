"""backend/reliability/idempotency.py — Idempotency key checker.

Prevents duplicate webhook deliveries from being processed twice.
The idempotency key is the GitHub ``X-GitHub-Delivery`` header (a UUID).

Storage backends (in priority order):
  1. PostgreSQL  — via ``idempotency_keys`` table (migrations/001_init.sql)
  2. In-memory   — fallback for local dev / tests (not suitable for multi-instance)

When a key is seen for the first time, it is stored with status="processing".
On completion the status is updated to "done".
Duplicate deliveries of a key in "processing" or "done" state raise
``IdempotencyConflictError``.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import uuid

from backend.core.exceptions import IdempotencyConflictError

logger = logging.getLogger(__name__)

_KEY_TTL_HOURS = 48  # keys expire after 48 h to prevent unbounded growth


class IdempotencyStore:
    """Checks and records idempotency keys.

    Inject a pool via ``set_pool()`` at startup; otherwise falls back to
    an in-memory dict (single-instance only).
    """

    def __init__(self):
        self._pool: Optional[Any] = None  # asyncpg.Pool
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def set_pool(self, pool: Any) -> None:
        self._pool = pool

    async def claim(self, delivery_id: str) -> None:
        """Claim a delivery_id; raises IdempotencyConflictError if already seen.

        Must be called before processing begins.  Call ``mark_done`` when
        processing is successfully complete.
        """
        if self._pool:
            await self._db_claim(delivery_id)
        else:
            await self._mem_claim(delivery_id)

    async def mark_done(self, delivery_id: str) -> None:
        """Mark processing of delivery_id as complete."""
        if self._pool:
            await self._db_mark_done(delivery_id)
        else:
            await self._mem_mark_done(delivery_id)

    async def get_status(self, delivery_id: str) -> Optional[str]:
        """Return current status of a delivery_id, or None if unknown."""
        if self._pool:
            return await self._db_get_status(delivery_id)
        async with self._lock:
            entry = self._memory.get(delivery_id)
            return entry["status"] if entry else None

    # ------------------------------------------------------------------
    # In-memory backend
    # ------------------------------------------------------------------

    async def _mem_claim(self, delivery_id: str) -> None:
        async with self._lock:
            entry = self._memory.get(delivery_id)
            if entry:
                raise IdempotencyConflictError(
                    f"Duplicate delivery: {delivery_id} already in status={entry['status']}"
                )
            self._memory[delivery_id] = {
                "status": "processing",
                "claimed_at": datetime.now(timezone.utc),
            }
            logger.debug("Idempotency: claimed key=%s", delivery_id)

    async def _mem_mark_done(self, delivery_id: str) -> None:
        async with self._lock:
            entry = self._memory.get(delivery_id)
            if entry:
                entry["status"] = "done"
                logger.debug("Idempotency: marked done key=%s", delivery_id)

    # ------------------------------------------------------------------
    # PostgreSQL backend
    # ------------------------------------------------------------------

    async def _db_claim(self, delivery_id: str) -> None:
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT status FROM idempotency_keys WHERE delivery_id = $1",
                    delivery_id,
                )
                if row:
                    raise IdempotencyConflictError(
                        f"Duplicate delivery: {delivery_id} already in status={row['status']}"
                    )
                await conn.execute(
                    """
                    INSERT INTO idempotency_keys (delivery_id, status, claimed_at, expires_at)
                    VALUES ($1, 'processing', NOW(), NOW() + INTERVAL '48 hours')
                    """,
                    delivery_id,
                )
                logger.debug("Idempotency DB: claimed key=%s", delivery_id)
        except IdempotencyConflictError:
            raise
        except Exception as exc:
            logger.error("Idempotency DB error on claim: %s — falling back to pass", exc)

    async def _db_mark_done(self, delivery_id: str) -> None:
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE idempotency_keys SET status = 'done' WHERE delivery_id = $1",
                    delivery_id,
                )
        except Exception as exc:
            logger.error("Idempotency DB error on mark_done: %s", exc)

    async def _db_get_status(self, delivery_id: str) -> Optional[str]:
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT status FROM idempotency_keys WHERE delivery_id = $1",
                    delivery_id,
                )
                return row["status"] if row else None
        except Exception as exc:
            logger.error("Idempotency DB error on get_status: %s", exc)
            return None

    async def purge_expired(self) -> int:
        """Delete expired idempotency keys.  Call from a scheduled maintenance job."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM idempotency_keys WHERE expires_at < NOW()"
                    )
                    deleted = int(result.split()[-1])
                    logger.info("Idempotency: purged %d expired keys", deleted)
                    return deleted
            except Exception as exc:
                logger.error("Idempotency purge error: %s", exc)
                return 0
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=_KEY_TTL_HOURS)
            async with self._lock:
                expired = [
                    k for k, v in self._memory.items()
                    if v["claimed_at"] < cutoff
                ]
                for k in expired:
                    del self._memory[k]
            return len(expired)


# Global singleton
idempotency_store = IdempotencyStore()
