"""
backend/economics/cost_repository.py — Spend Aggregator & Observability cost metrics.

Enforces:
  - Calculation of cumulative cost from recorded event logs
  - Retrieval of agent-specific cost statistics
"""

import uuid
from typing import Dict

from backend.observability.events import event_tracker


class CostRepository:
    """Aggregates cost statistics from tracked events in the event spine."""

    def get_review_cost(self, review_id: uuid.UUID) -> float:
        """Sum the total cost in USD for a specific review pipeline execution."""
        total = 0.0
        for event in event_tracker.get_events():
            if event.review_id == review_id and event.cost_usd:
                total += event.cost_usd
        return round(total, 6)

    def get_daily_cost(self) -> float:
        """Sum the total cost in USD for all review executions recorded in the tracker."""
        total = 0.0
        for event in event_tracker.get_events():
            if event.cost_usd:
                total += event.cost_usd
        return round(total, 6)

    def get_cost_by_agent(self) -> Dict[str, float]:
        """Aggregate total token spend by specialist agent types."""
        costs: Dict[str, float] = {}
        for event in event_tracker.get_events():
            if event.cost_usd:
                costs[event.agent] = costs.get(event.agent, 0.0) + event.cost_usd

        # Round results
        return {agent: round(cost, 6) for agent, cost in costs.items()}
