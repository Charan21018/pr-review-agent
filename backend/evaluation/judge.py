"""backend/evaluation/judge.py — LLM-as-a-judge and rule-based finding scorer.

Computes precision, recall, and F1 scores by comparing generated findings
with golden PR ground truth findings.
"""
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from backend.models.findings import Finding
from backend.evaluation.golden_dataset import GroundTruthFinding

class EvaluationScore(BaseModel):
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class Judge:
    """Scorer that compares agent outputs to expected findings."""

    @staticmethod
    def evaluate_findings(actual: List[Finding], expected: List[GroundTruthFinding]) -> EvaluationScore:
        """Calculates exact/fuzzy match scoring for findings.

        A finding is a true positive (TP) if there exists a ground truth finding with
        the same file_path and category/agent_type, and overlapping lines.
        """
        if not expected:
            precision = 1.0 if not actual else 0.0
            return EvaluationScore(precision=precision, recall=1.0, f1=precision, true_positives=0, false_positives=len(actual), false_negatives=0)

        if not actual:
            return EvaluationScore(precision=1.0, recall=0.0, f1=0.0, true_positives=0, false_positives=0, false_negatives=len(expected))

        tps = 0
        fps = 0
        matched_expected = set()

        for act in actual:
            match_found = False
            for idx, exp in enumerate(expected):
                if idx in matched_expected:
                    continue
                
                # Check path and category
                path_match = act.file_path.strip("/") == exp.file_path.strip("/")
                cat_match = act.category.lower() == exp.category.lower() or act.agent_type == exp.agent_type

                # Check line overlap (if lines specified)
                line_overlap = True
                if act.line_start is not None and exp.line_start is not None:
                    # Overlap if max(start1, start2) <= min(end1, end2)
                    act_end = act.line_end if act.line_end is not None else act.line_start
                    exp_end = exp.line_end if exp.line_end is not None else exp.line_start
                    line_overlap = max(act.line_start, exp.line_start) <= min(act_end, exp_end)

                if path_match and cat_match and line_overlap:
                    tps += 1
                    matched_expected.add(idx)
                    match_found = True
                    break
            
            if not match_found:
                fps += 1

        fns = len(expected) - len(matched_expected)
        
        precision = tps / (tps + fps) if (tps + fps) > 0 else 0.0
        recall = tps / (tps + fns) if (tps + fns) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return EvaluationScore(
            precision=precision,
            recall=recall,
            f1=f1,
            true_positives=tps,
            false_positives=fps,
            false_negatives=fns
        )
