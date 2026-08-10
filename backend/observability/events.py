"""
backend/observability/events.py — Observability Event Tracker & Spine Recorder.

Enforces:
- Invariant I3: Single source of truth for cost, latency, and decisions
- Structure validation of event rows
- Persists events to Tiger Cloud (TimescaleDB) agent_events hypertable
"""
from datetime import datetime, timezone
import uuid
import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import asyncpg

class AgentEvent:

    def __init__(
        self,
        review_id: uuid.UUID,
        agent: str,
        event_type: str,
        span_id: uuid.UUID,
        parent_span: Optional[uuid.UUID] = None,
        model: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        cost_usd: Optional[float] = None,
        latency_ms: Optional[int] = None,
        outcome: Optional[str] = None,
        confidence: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
        ts: Optional[datetime] = None,
    ):
        self.ts = ts or datetime.now(timezone.utc)
        self.review_id = review_id
        self.agent = agent
        self.event_type = event_type
        self.span_id = span_id
        self.parent_span = parent_span
        self.model = model
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.outcome = outcome
        self.confidence = confidence
        self.payload = payload or {}


class AwaitableEvent:
    """A wrapper that allows a function call to be awaited or used synchronously."""
    def __init__(self, event: AgentEvent, coro=None):
        self.event = event
        self.coro = coro

    def __await__(self):
        if self.coro:
            return self.coro.__await__()
        async def _dummy():
            return self.event
        return _dummy().__await__()

    def __getattr__(self, name):
        # Proxy attribute access to the underlying AgentEvent
        return getattr(self.event, name)


class EventTracker:
    """Manages tracking of span lifecycle and LLM metrics, writing to the event spine."""

    def __init__(self):
        self._mock_events: List[AgentEvent] = []
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> Optional[asyncpg.Pool]:
        if self._pool is None:
            url = os.getenv("TIGER_DATABASE_URL", "")
            if not url:
                return None
            # Strip ssl parameter for asyncpg compatibility
            if "ssl=" in url:
                import urllib.parse as up
                parts = list(up.urlparse(url))
                q = dict(up.parse_qsl(parts[4]))
                q.pop("ssl", None)
                parts[4] = up.urlencode(q)
                url = up.urlunparse(parts)
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            try:
                self._pool = await asyncpg.create_pool(url, ssl=True, min_size=1, max_size=5)
            except Exception as e:
                print(f"[Warning] EventTracker failed to create DB pool: {e}")
        return self._pool

    async def persist_event_async(self, event: AgentEvent) -> None:
        """Insert the event into the agent_events hypertable in Tiger Cloud."""
        pool = await self._get_pool()
        if pool is None:
            return

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_events (
                        id, ts, review_id, agent, event_type, span_id, parent_span,
                        model, tokens_in, tokens_out, cost_usd, latency_ms,
                        outcome, confidence, payload
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12,
                        $13, $14, $15
                    )
                    """,
                    uuid.uuid4(),
                    event.ts,
                    event.review_id,
                    event.agent,
                    event.event_type,
                    event.span_id,
                    event.parent_span,
                    event.model,
                    event.tokens_in,
                    event.tokens_out,
                    event.cost_usd,
                    event.latency_ms,
                    event.outcome,
                    event.confidence,
                    json.dumps(event.payload)
                )
        except Exception as e:
            print(f"[Warning] Failed to persist event to agent_events table: {e}")

    def clear(self):
        self._mock_events.clear()

    def get_events(self) -> List[AgentEvent]:
        return self._mock_events

    def track_span_start(
        self,
        review_id: uuid.UUID,
        agent: str,
        span_id: uuid.UUID,
        parent_span: Optional[uuid.UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AwaitableEvent:
        event = AgentEvent(
            review_id=review_id,
            agent=agent,
            event_type="span.start",
            span_id=span_id,
            parent_span=parent_span,
            payload=payload,
        )
        self._mock_events.append(event)
        
        coro = None
        if os.getenv("TIGER_DATABASE_URL"):
            coro = self.persist_event_async(event)
        return AwaitableEvent(event, coro)

    def track_span_end(
        self,
        review_id: uuid.UUID,
        agent: str,
        span_id: uuid.UUID,
        latency_ms: int,
        outcome: Optional[str] = None,
        confidence: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AwaitableEvent:
        event = AgentEvent(
            review_id=review_id,
            agent=agent,
            event_type="span.end",
            span_id=span_id,
            latency_ms=latency_ms,
            outcome=outcome,
            confidence=confidence,
            payload=payload,
        )
        self._mock_events.append(event)
        
        coro = None
        if os.getenv("TIGER_DATABASE_URL"):
            coro = self.persist_event_async(event)
        return AwaitableEvent(event, coro)

    def track_llm_call(
        self,
        review_id: uuid.UUID,
        agent: str,
        span_id: uuid.UUID,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        latency_ms: int,
    ) -> AwaitableEvent:
        event = AgentEvent(
            review_id=review_id,
            agent=agent,
            event_type="llm.call",
            span_id=span_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
        self._mock_events.append(event)
        
        coro = None
        if os.getenv("TIGER_DATABASE_URL"):
            coro = self.persist_event_async(event)
        return AwaitableEvent(event, coro)


# Global tracker instance
event_tracker = EventTracker()
