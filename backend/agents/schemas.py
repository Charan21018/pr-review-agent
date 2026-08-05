"""
backend/agents/schemas.py — Data contracts for specialist findings and aggregated reviews.

Enforces:
  - Strict type checking and validation for LLM outputs
  - Enum-bounded severity values
  - Confidence scoring between 0.0 and 1.0
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Finding(BaseModel):
    specialist: str = Field(description="Name of specialist agent (security|quality|tests|docs)")
    severity: SeverityEnum = Field(description="Severity classification")
    category: str = Field(description="Category of issue (e.g., SQL Injection, Code Style, Test Coverage)")
    file_path: Optional[str] = Field(default=None, description="File path relative to repository root")
    line_start: Optional[int] = Field(default=None, description="Starting line number")
    line_end: Optional[int] = Field(default=None, description="Ending line number")
    rationale: str = Field(description="Clear explanation of why this issue matters and how to fix it")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")


class AggregatedReview(BaseModel):
    summary: str = Field(description="Executive summary of the PR review")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Aggregated confidence score")
    has_critical: bool = Field(description="True if any finding has CRITICAL severity")
    recommendation: str = Field(description="APPROVE | REQUEST_CHANGES | ESCALATE_TO_HUMAN")
    findings: List[Finding] = Field(default_factory=list, description="Deduplicated list of findings across all specialists")
