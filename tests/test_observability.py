"""
tests/test_observability.py — Acceptance and unit tests for EventTracker, CostRepository, and BudgetGuard.

Covers:
  - EventTracker: span tracking and LLM metadata updates
  - CostRepository: daily spend calculations, review aggregates, and agent grouping
  - BudgetGuard: limit validation and synchronous blocking behavior (PermissionError)
"""

import uuid
import pytest

from backend.economics.budget_guard import BudgetGuard
from backend.economics.cost_repository import CostRepository
from backend.observability.events import event_tracker


@pytest.fixture(autouse=True)
def clean_events():
    """Clear event tracker log between test runs."""
    event_tracker.clear()
    yield
    event_tracker.clear()


class TestEventTracker:

    def test_track_span_lifecycle(self):
        review_id = uuid.uuid4()
        span_id = uuid.uuid4()

        event_tracker.track_span_start(review_id, "security", span_id)
        event_tracker.track_span_end(review_id, "security", span_id, latency_ms=1200, outcome="approved")

        events = event_tracker.get_events()
        assert len(events) == 2
        assert events[0].event_type == "span.start"
        assert events[1].event_type == "span.end"
        assert events[1].latency_ms == 1200
        assert events[1].outcome == "approved"

    def test_track_llm_call(self):
        review_id = uuid.uuid4()
        span_id = uuid.uuid4()

        event_tracker.track_llm_call(
            review_id,
            "quality",
            span_id,
            model="claude-haiku-4-5",
            tokens_in=100,
            tokens_out=200,
            cost_usd=0.0015,
            latency_ms=900,
        )

        events = event_tracker.get_events()
        assert len(events) == 1
        assert events[0].event_type == "llm.call"
        assert events[0].cost_usd == 0.0015
        assert events[0].model == "claude-haiku-4-5"


class TestCostRepository:

    def test_cost_aggregations(self):
        r1 = uuid.uuid4()
        r2 = uuid.uuid4()
        s_id = uuid.uuid4()

        # Review 1 events
        event_tracker.track_llm_call(r1, "security", s_id, "model", 100, 100, 0.002, 100)
        event_tracker.track_llm_call(r1, "quality", s_id, "model", 100, 100, 0.003, 100)

        # Review 2 event
        event_tracker.track_llm_call(r2, "security", s_id, "model", 100, 100, 0.005, 100)

        cost_repo = CostRepository()

        assert cost_repo.get_review_cost(r1) == 0.005
        assert cost_repo.get_review_cost(r2) == 0.005
        assert cost_repo.get_daily_cost() == 0.010

        agent_costs = cost_repo.get_cost_by_agent()
        assert agent_costs["security"] == 0.007
        assert agent_costs["quality"] == 0.003


class TestBudgetGuard:

    def test_budget_checks(self):
        r1 = uuid.uuid4()
        s_id = uuid.uuid4()

        cost_repo = CostRepository()
        guard = BudgetGuard(cost_repo, daily_limit_usd=0.010)

        assert guard.is_within_budget() is True
        guard.validate_and_block()

        # Log calls that exceed daily limit
        event_tracker.track_llm_call(r1, "security", s_id, "model", 100, 100, 0.008, 100)
        event_tracker.track_llm_call(r1, "quality", s_id, "model", 100, 100, 0.004, 100)

        assert guard.is_within_budget() is False
        with pytest.raises(PermissionError) as excinfo:
            guard.validate_and_block()
        assert "exceeded" in str(excinfo.value)
