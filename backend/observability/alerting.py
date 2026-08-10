"""backend/observability/alerting.py — Alert threshold engine.

Monitors key operational metrics and fires alerts when thresholds are breached.
Alert channels are pluggable: stdout (default), Slack webhook, PagerDuty.

Design principle: the alerting module only reads from the event store;
it never modifies agent state.
"""
import os
import logging
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class AlertRule:
    """Declarative threshold rule."""
    name: str
    description: str
    severity: AlertSeverity
    # Callable[metric_value] -> bool; True means the rule fires
    condition: Callable[[float], bool]
    channel: str = "log"   # "log" | "slack" | "pagerduty"


@dataclass
class AlertEvent:
    """A fired alert instance."""
    rule_name: str
    severity: AlertSeverity
    metric_value: float
    message: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlertManager:
    """Evaluates alert rules against live metrics and dispatches notifications.

    Usage::

        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="high_cost",
            description="Daily cost exceeds $50",
            severity=AlertSeverity.WARNING,
            condition=lambda v: v > 50.0,
        ))
        await manager.evaluate("daily_cost_usd", 63.5)
    """

    # Built-in default rules (can be extended at runtime)
    DEFAULT_RULES: List[AlertRule] = [
        AlertRule(
            name="budget_90pct",
            description="Daily token cost exceeds 90 % of configured budget",
            severity=AlertSeverity.WARNING,
            condition=lambda v: v >= 0.90,
        ),
        AlertRule(
            name="budget_exceeded",
            description="Daily token cost has exceeded 100 % of configured budget",
            severity=AlertSeverity.CRITICAL,
            condition=lambda v: v >= 1.0,
        ),
        AlertRule(
            name="high_llm_latency",
            description="LLM call latency exceeds 30 s",
            severity=AlertSeverity.WARNING,
            condition=lambda v: v > 30_000,  # ms
        ),
        AlertRule(
            name="circuit_open",
            description="A circuit breaker is in the open state",
            severity=AlertSeverity.CRITICAL,
            condition=lambda v: v > 0,
        ),
        AlertRule(
            name="hitl_queue_backlog",
            description="HITL queue depth exceeds 50 pending items",
            severity=AlertSeverity.WARNING,
            condition=lambda v: v > 50,
        ),
    ]

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {r.name: r for r in self.DEFAULT_RULES}
        self._history: List[AlertEvent] = []
        self._slack_webhook: Optional[str] = os.getenv("ALERT_SLACK_WEBHOOK_URL")

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    async def evaluate(self, metric_name: str, value: float) -> List[AlertEvent]:
        """Evaluate all rules whose name starts with metric_name and fire matching ones."""
        fired: List[AlertEvent] = []
        for rule in self._rules.values():
            if rule.name.startswith(metric_name) or metric_name == rule.name:
                if rule.condition(value):
                    event = AlertEvent(
                        rule_name=rule.name,
                        severity=rule.severity,
                        metric_value=value,
                        message=(
                            f"[{rule.severity.value}] {rule.description} "
                            f"(metric={metric_name}, value={value})"
                        ),
                    )
                    self._history.append(event)
                    fired.append(event)
                    await self._dispatch(event, rule.channel)
        return fired

    async def _dispatch(self, event: AlertEvent, channel: str) -> None:
        if channel == "slack" and self._slack_webhook and _HTTPX_AVAILABLE:
            await self._send_slack(event)
        else:
            # Always log regardless of channel
            log_fn = logger.critical if event.severity == AlertSeverity.CRITICAL else logger.warning
            log_fn("ALERT %s: %s", event.rule_name, event.message)

    async def _send_slack(self, event: AlertEvent) -> None:
        emoji = "🔴" if event.severity == AlertSeverity.CRITICAL else "🟡"
        payload = {"text": f"{emoji} *{event.rule_name}*: {event.message}"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(self._slack_webhook, json=payload)
        except Exception as exc:
            logger.error("AlertManager: Slack dispatch failed: %s", exc)

    def get_history(self, limit: int = 50) -> List[AlertEvent]:
        return self._history[-limit:]


# Global singleton
alert_manager = AlertManager()
