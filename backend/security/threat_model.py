"""backend/security/threat_model.py — Threat definitions and risk classifications.

Quantifies and defines threat classifications for the review agent.
Aides injection_guard and specialized security agents in grading issues.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SECRET_LEAK = "secret_leak"
    INSECURE_DEPENDENCY = "insecure_dependency"
    CODE_VULNERABILITY = "code_vulnerability"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"

class ThreatDefinition(BaseModel):
    category: ThreatCategory
    risk_level: RiskLevel
    description: str
    mitigation_strategy: str

# Static database of threat rules
THREAT_REGISTRY = {
    "injection": ThreatDefinition(
        category=ThreatCategory.PROMPT_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="Malicious instructions embedded in PR diff or comments attempting to hijack the reviewer agent.",
        mitigation_strategy="Sanitize inputs, reject/flag review task immediately, notify security channel."
    ),
    "credentials": ThreatDefinition(
        category=ThreatCategory.SECRET_LEAK,
        risk_level=RiskLevel.CRITICAL,
        description="Plaintext API keys, passwords, Private keys, or Bearer tokens detected in codebase.",
        mitigation_strategy="Revoke credentials immediately, filter out of review comments to prevent logging, trigger rotation."
    ),
    "dependency_cve": ThreatDefinition(
        category=ThreatCategory.INSECURE_DEPENDENCY,
        risk_level=RiskLevel.HIGH,
        description="Packages with known high/critical CVEs added to requirements or package files.",
        mitigation_strategy="Block PR merge, recommend upgrade paths to patched versions."
    ),
    "owasp_top_10": ThreatDefinition(
        category=ThreatCategory.CODE_VULNERABILITY,
        risk_level=RiskLevel.HIGH,
        description="SQL Injection, XSS, SSRF, or Path Traversal vulnerability detected in source code changes.",
        mitigation_strategy="Create high-severity finding pointing to vulnerable lines, suggest parameterized queries or sanitization."
    )
}

def determine_risk(confidence: float, category_key: str) -> RiskLevel:
    """Helper to scale or determine risk based on tool confidence and threat severity."""
    definition = THREAT_REGISTRY.get(category_key)
    if not definition:
        return RiskLevel.LOW
    if confidence > 0.8:
        return definition.risk_level
    elif confidence > 0.5:
        # Downgrade risk level by one notch if confidence is medium
        if definition.risk_level == RiskLevel.CRITICAL:
            return RiskLevel.HIGH
        elif definition.risk_level == RiskLevel.HIGH:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    return RiskLevel.LOW
