"""backend/evaluation/golden_dataset.py — Golden PR datasets for evaluation.

Defines the structure of target PRs and expected ground-truth findings,
enabling regression testing of specialist agents.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.models.enums import Severity, AgentType

class GroundTruthFinding(BaseModel):
    category: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    agent_type: AgentType

class GoldenPR(BaseModel):
    id: str
    repo: str
    pr_number: int
    pr_diff: str
    ground_truth: List[GroundTruthFinding] = Field(default_factory=list)

# Mock golden PR dataset for CI and regression evaluation
GOLDEN_DATASET: List[GoldenPR] = [
    GoldenPR(
        id="golden-001-injection",
        repo="owner/repo",
        pr_number=101,
        pr_diff="""diff --git a/src/db.py b/src/db.py
index e69de29..8004f13 100644
--- a/src/db.py
+++ b/src/db.py
@@ -10,3 +10,6 @@ def get_user(user_id):
-    query = "SELECT * FROM users WHERE id = ?"
-    return db.execute(query, [user_id])
+    # Vulnerable SQL concatenation
+    query = "SELECT * FROM users WHERE id = " + user_id
+    return db.execute(query)
""",
        ground_truth=[
            GroundTruthFinding(
                category="injection",
                file_path="src/db.py",
                line_start=11,
                line_end=13,
                severity=Severity.CRITICAL,
                agent_type=AgentType.SECURITY
            )
        ]
    ),
    GoldenPR(
        id="golden-002-missing-test",
        repo="owner/repo",
        pr_number=102,
        pr_diff="""diff --git a/src/utils.py b/src/utils.py
index e69de29..8004f13 100644
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,5 +1,9 @@
 def parse_date(date_str):
+    # Complex date parsing function added without writing any tests
     try:
         return datetime.strptime(date_str, "%Y-%m-%d")
     except Exception:
         return None
""",
        ground_truth=[
            GroundTruthFinding(
                category="missing-test",
                file_path="src/utils.py",
                line_start=1,
                line_end=6,
                severity=Severity.LOW,
                agent_type=AgentType.TESTS
            )
        ]
    )
]

def get_golden_pr(pr_id: str) -> Optional[GoldenPR]:
    """Retrieves a single golden PR by its ID."""
    for pr in GOLDEN_DATASET:
        if pr.id == pr_id:
            return pr
    return None
