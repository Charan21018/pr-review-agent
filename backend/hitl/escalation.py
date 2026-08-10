"""backend/hitl/escalation.py — Escalation engine for PR review agent.

Implements rules to route reviews to the HITL queue based on confidence score,
finding severity, and agent categories.
"""
import logging
import uuid
from typing import List, Tuple, Union
from backend.models.findings import Finding
from backend.models.enums import Severity
from backend.hitl.queue import hitl_queue

logger = logging.getLogger(__name__)

# Configurable thresholds
CONFIDENCE_THRESHOLD_HIGH = 0.75  # Escalation if HIGH severity finding has confidence < 0.75
CONFIDENCE_THRESHOLD_MEDIUM = 0.60 # Escalation if MEDIUM severity finding has confidence < 0.60

class EscalationEngine:
    """Evaluates findings to decide if human reviewer validation is required."""

    @staticmethod
    async def evaluate_and_escalate(review_id: Union[str, uuid.UUID], findings: List[Finding]) -> Tuple[bool, str]:
        """Runs the rule engine on findings.

        Returns (should_escalate, reason). Enqueues item automatically if True.
        """
        review_uuid = uuid.UUID(str(review_id)) if not isinstance(review_id, uuid.UUID) else review_id

        # Rule 1: Escalation on CRITICAL severity
        for f in findings:
            if f.severity == Severity.CRITICAL:
                reason = f"CRITICAL finding detected: '{f.summary}' in {f.file_path}"
                logger.info("EscalationEngine: Escalating review %s due to CRITICAL severity finding.", review_uuid)
                await hitl_queue.enqueue(review_uuid, reason)
                return True, reason

        # Rule 2: Escalation on LOW CONFIDENCE for High/Medium issues
        for f in findings:
            if f.severity == Severity.HIGH and f.confidence < CONFIDENCE_THRESHOLD_HIGH:
                reason = f"Low confidence ({f.confidence:.2f} < {CONFIDENCE_THRESHOLD_HIGH}) on HIGH severity finding: '{f.summary}'"
                logger.info("EscalationEngine: Escalating review %s due to low confidence on HIGH finding.", review_uuid)
                await hitl_queue.enqueue(review_uuid, reason)
                return True, reason
                
            if f.severity == Severity.MEDIUM and f.confidence < CONFIDENCE_THRESHOLD_MEDIUM:
                reason = f"Low confidence ({f.confidence:.2f} < {CONFIDENCE_THRESHOLD_MEDIUM}) on MEDIUM severity finding: '{f.summary}'"
                logger.info("EscalationEngine: Escalating review %s due to low confidence on MEDIUM finding.", review_uuid)
                await hitl_queue.enqueue(review_uuid, reason)
                return True, reason

        # Rule 3: Zero findings but overall check requires a sample check (can be custom flag, skipped for now)
        return False, ""
