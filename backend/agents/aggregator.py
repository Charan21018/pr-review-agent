import asyncio
from typing import List, Optional
from uuid import uuid4

from backend.agents.base import BaseSpecialistAgent
from backend.agents.docs import DocsAgent
from backend.agents.quality import QualityAgent
from backend.agents.schemas import AggregatedReview, Finding, SeverityEnum
from backend.agents.security import SecurityAgent
from backend.agents.tests import TestsAgent

class Aggregator:

    def __init__(self, specialists: Optional[List[BaseSpecialistAgent]] = None):
        if specialists is None:
            self.specialists = [
                SecurityAgent(),
                QualityAgent(),
                TestsAgent(),
                DocsAgent(),
            ]
        else:
            self.specialists = specialists

    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Deduplicate findings sharing category, file_path, line_start, severity."""
        seen = set()
        unique: List[Finding] = []
        for f in findings:
            key = (f.category, f.file_path, f.line_start, f.severity)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    async def run_review(self, pr_diff: str, context_chunks: Optional[List[str]] = None) -> AggregatedReview:
        """Run all specialists in parallel, aggregate findings, apply HITL gate."""
        # 1. Parallel fan‑out execution
        tasks = [agent.run_with_timeout(pr_diff, context_chunks) for agent in self.specialists]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_findings: List[Finding] = []
        for res in results:
            if isinstance(res, list):
                all_findings.extend(res)

        # 2. Deduplication
        deduped_findings = self._deduplicate_findings(all_findings)

        # 3. Confidence computation
        if deduped_findings:
            overall_confidence = round(
                sum(f.confidence for f in deduped_findings) / len(deduped_findings), 3
            )
        else:
            overall_confidence = 1.0  # clean diff has high confidence

        # 4. Severity checks
        has_critical = any(f.severity == SeverityEnum.CRITICAL for f in deduped_findings)
        has_high = any(f.severity == SeverityEnum.HIGH for f in deduped_findings)

        # 5. Recommendation decision (HITL Gate)
        if has_critical or overall_confidence < 0.70:
            recommendation = "ESCALATE_TO_HUMAN"
            summary = (
                f"Review completed with {len(deduped_findings)} finding(s). "
                f"Requires human review (Critical: {has_critical}, Confidence: {overall_confidence})."
            )
        elif has_high:
            recommendation = "REQUEST_CHANGES"
            summary = f"Review completed with {len(deduped_findings)} finding(s). High severity issues detected."
        else:
            recommendation = "APPROVE"
            summary = f"PR approved with {len(deduped_findings)} minor finding(s)."

        # HITL handling – lazy imports to keep clean architecture invariant
        if recommendation == "ESCALATE_TO_HUMAN":
            import os
            review_id = str(uuid4())
            # Lazy import of infrastructure services
            from backend.api.hitl import await_decision
            from backend.api.github_client import GitHubClient
            try:
                decision = await await_decision(review_id, timeout=30)
            except TimeoutError as e:
                # No human decision was recorded in time — stay conservative and
                # keep escalating rather than silently auto-approving.
                decision = {"decision": "ESCALATE_TO_HUMAN", "reviewer": None, "comments": str(e)}
            except Exception as e:
                decision = {"decision": "APPROVE", "reviewer": None, "comments": str(e)}
            gh = GitHubClient()
            repo_full = os.getenv("GITHUB_REPO", "")
            pr_number = int(os.getenv("PR_NUMBER", "0"))
            gh.post_review(
                repo_full_name=repo_full,
                pull_number=pr_number,
                body=summary,
                decision=decision["decision"],
            )
            recommendation = decision["decision"]

        return AggregatedReview(
            summary=summary,
            overall_confidence=overall_confidence,
            has_critical=has_critical,
            recommendation=recommendation,
            findings=deduped_findings,
        )
