"""backend/models/enums.py — Canonical enums used across all modules."""
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AgentType(str, Enum):
    SECURITY = "security"
    QUALITY = "quality"
    TESTS = "tests"
    DOCS = "docs"
    AGGREGATOR = "aggregator"
    SYSTEM = "system"


class EventType(str, Enum):
    SPAN_START = "span.start"
    SPAN_END = "span.end"
    LLM_CALL = "llm.call"
    TOOL_CALL = "tool.call"
    DECISION = "decision"
    ESCALATION = "escalation"


class Outcome(str, Enum):
    APPROVED = "approved"
    REQUEST_CHANGES = "request_changes"
    ESCALATED = "escalated"
    CRITICAL_BLOCK = "critical_block"
    REJECTED = "rejected"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class HitlDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
