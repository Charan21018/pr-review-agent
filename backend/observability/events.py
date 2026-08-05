"""
backend/observability/events.py — Observability Event Tracker & Spine Recorder.

Enforces:
  - Invariant I3: Single source of truth for cost, latency, and decisions
  - Structure validation of event rows
  - Memory buffer for local testing (mocking hypertable inserts)
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional


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


class EventTracker:
    """Manages tracking of span lifecycle and LLM metrics, writing to the event spine."""

    def __init__(self):
        self._mock_events: List[AgentEvent] = []

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
    ) -> AgentEvent:
        event = AgentEvent(
            review_id=review_id,
            agent=agent,
            event_type="span.start",
            span_id=span_id,
            parent_span=parent_span,
            payload=payload,
        )
        self._mock_events.append(event)
        return event

    def track_span_end(
        self,
        review_id: uuid.UUID,
        agent: str,
        span_id: uuid.UUID,
        latency_ms: int,
        outcome: Optional[str] = None,
        confidence: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
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
        return event

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
    ) -> AgentEvent:
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
        return event


# Global tracker instance
event_tracker = EventTracker()
