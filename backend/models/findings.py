"""backend/models/findings.py — Canonical Finding Pydantic contract (L2 of design doc).

Every specialist agent returns a list of Finding objects. The aggregator merges them.
Every field traces back to a justified design decision:
  - agent_type: attribution for grouping and audit
  - severity + category: what and how bad
  - file_path + line_start/end: inline GitHub comment placement
  - confidence + rationale: drives the HITL gate (L7) and is the proof layer (L6)
  - suggestion: actionable output for the developer
"""
from pydantic import BaseModel, Field
from typing import Optional
from backend.models.enums import Severity, AgentType


class Finding(BaseModel):
    """The unit that flows through the system. Structured output, not prose."""

    agent_type: AgentType = Field(..., description="Which specialist raised this finding")
    severity: Severity = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW | INFO")
    category: str = Field(..., description="E.g. 'injection', 'missing-test', 'undocumented-api'")
    summary: str = Field(..., description="One-sentence description of the finding")
    file_path: str = Field(..., description="Relative path in the repo, e.g. 'src/auth.py'")
    line_start: Optional[int] = Field(None, description="Start line for inline comment placement")
    line_end: Optional[int] = Field(None, description="End line for inline comment placement")
    suggestion: Optional[str] = Field(None, description="Actionable fix suggestion for the developer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0.0–1.0 confidence score drives HITL gate")
    rationale: str = Field(..., description="Evidence-backed explanation — what makes it auditable")

    def is_critical_block(self) -> bool:
        """A CRITICAL finding always escalates regardless of confidence (L7)."""
        return self.severity == Severity.CRITICAL

    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "security",
                "severity": "CRITICAL",
                "category": "injection",
                "summary": "SQL injection via unsanitized user input in query builder",
                "file_path": "src/db/queries.py",
                "line_start": 42,
                "line_end": 45,
                "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', [user_id])",
                "confidence": 0.95,
                "rationale": "Line 43 concatenates user_input directly into the SQL string without sanitization.",
            }
        }
