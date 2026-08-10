"""backend/evaluation/regression_gate.py — CI Regression gate check.

Loads the golden dataset, runs the review pipeline or simulates execution,
computes metrics using Judge, and asserts performance thresholds (e.g. F1 >= 0.85).
"""
import logging
from typing import Dict, Any, List
from backend.evaluation.golden_dataset import GOLDEN_DATASET
from backend.evaluation.judge import Judge, EvaluationScore
from backend.core.exceptions import ReviewAgentError

logger = logging.getLogger(__name__)

class RegressionGateError(ReviewAgentError):
    """Raised when the regression gate threshold check fails."""
    pass

class RegressionGate:
    """CI/CD Gate verifying quality metric levels on change sets."""

    def __init__(self, f1_threshold: float = 0.85):
        self.f1_threshold = f1_threshold

    async def run_regression_test(self, workflow_runner: Any) -> Dict[str, Any]:
        """Runs the whole golden dataset against the given workflow runner and computes scores.

        workflow_runner must implement: run(workflow_id: str, input_data: dict) -> state
        """
        logger.info("RegressionGate: Starting regression tests on %d golden PRs...", len(GOLDEN_DATASET))
        
        passed = True
        results = []
        total_tps = 0
        total_fps = 0
        total_fns = 0

        for pr in GOLDEN_DATASET:
            input_data = {
                "repo": pr.repo,
                "pr_number": pr.pr_number,
                "pr_diff": pr.pr_diff,
                "review_id": pr.id
            }
            try:
                # Execute the workflow
                state = await workflow_runner.run(workflow_id=pr.id, input_data=input_data)
                actual_findings = state.get("findings", [])
                
                # Evaluate results
                score = Judge.evaluate_findings(actual_findings, pr.ground_truth)
                results.append({
                    "pr_id": pr.id,
                    "score": score.to_dict(),
                    "findings_count": len(actual_findings),
                    "error": None
                })
                
                total_tps += score.true_positives
                total_fps += score.false_positives
                total_fns += score.false_negatives

            except Exception as e:
                logger.error("RegressionGate: Error running golden PR %s: %s", pr.id, e)
                passed = False
                results.append({
                    "pr_id": pr.id,
                    "score": None,
                    "findings_count": 0,
                    "error": str(e)
                })

        # Calculate macro metrics
        precision = total_tps / (total_tps + total_fps) if (total_tps + total_fps) > 0 else 0.0
        recall = total_tps / (total_tps + total_fns) if (total_tps + total_fns) > 0 else 0.0
        macro_f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        gate_passed = passed and (macro_f1 >= self.f1_threshold)
        
        report = {
            "passed": gate_passed,
            "macro_precision": precision,
            "macro_recall": recall,
            "macro_f1": macro_f1,
            "f1_threshold": self.f1_threshold,
            "details": results
        }

        if not gate_passed:
            msg = f"Regression gate failed! F1 Score {macro_f1:.2f} is below threshold {self.f1_threshold:.2f} or errors occurred."
            logger.error("RegressionGate: %s", msg)
            raise RegressionGateError(msg)

        logger.info("RegressionGate: Passed! Macro F1 Score: %.2f", macro_f1)
        return report
