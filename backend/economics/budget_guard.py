"""
backend/economics/budget_guard.py — Token Budget Guard & Limit Enforcer.

Enforces:
  - Daily cost cap validation
  - Invariant I2: Outbound budget tracking is synchronous and blocks subsequent requests
"""

from backend.economics.cost_repository import CostRepository


class BudgetGuard:
    """Monitors daily spend totals and halts pipeline execution if cap is reached."""

    def __init__(self, cost_repo: CostRepository, daily_limit_usd: float = 10.0):
        self.cost_repo = cost_repo
        self.daily_limit_usd = daily_limit_usd

    def is_within_budget(self) -> bool:
        """Check if current total daily spend is within bounds."""
        current_spend = self.cost_repo.get_daily_cost()
        return current_spend < self.daily_limit_usd

    def validate_and_block(self):
        """Raise an exception if the budget limit is breached, blocking execution (I2 invariant)."""
        current_spend = self.cost_repo.get_daily_cost()
        if current_spend >= self.daily_limit_usd:
            raise PermissionError(
                f"Daily token budget cap of ${self.daily_limit_usd:.4f} exceeded. "
                f"Current spend: ${current_spend:.4f}."
            )
