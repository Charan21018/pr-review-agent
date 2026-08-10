"""backend/security/masking.py — Secret and PII masking.

Redacts credentials, API keys, passwords, and sensitive keys from logs,
payloads, and comments before they are persisted or displayed in the UI.
"""
import re
from typing import Any, Dict, List, Union

# Common credential patterns
SECRET_PATTERNS = [
    # General API keys
    (r"(?i)(api[_-]?key|client[_-]?secret|password|secret[_-]?token|bearer|auth[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", r"\1: '***REDACTED***'"),
    # AWS Access Key ID
    (r"\b(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b", "[AWS-KEY-REDACTED]"),
    # AWS Secret Access Key
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]", "aws_secret_access_key: '***REDACTED***'"),
    # Generic Private Key
    (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", "[PRIVATE-KEY-REDACTED]"),
    # GitHub Token
    (r"\b(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,251}\b", "[GITHUB-TOKEN-REDACTED]"),
    # Slack Webhook / App tokens
    (r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+", "https://hooks.slack.com/services/***REDACTED***")
]

def mask_secrets(text: str) -> str:
    """Scan and redact known secrets in a string."""
    if not text:
        return text

    masked = text
    for pattern, replacement in SECRET_PATTERNS:
        masked = re.sub(pattern, replacement, masked)
    return masked

def mask_payload(data: Union[Dict[str, Any], List[Any], str, int, float, bool, None]) -> Any:
    """Deeply masks sensitive fields in generic JSON-like structures."""
    if isinstance(data, dict):
        masked_dict = {}
        for k, v in data.items():
            # Check if key implies sensitive data
            k_lower = k.lower()
            if any(term in k_lower for term in ["key", "secret", "password", "token", "auth", "credential", "private"]):
                if isinstance(v, str):
                    masked_dict[k] = "***REDACTED***"
                else:
                    masked_dict[k] = v
            else:
                masked_dict[k] = mask_payload(v)
        return masked_dict
    elif isinstance(data, list):
        return [mask_payload(item) for item in data]
    elif isinstance(data, str):
        return mask_secrets(data)
    else:
        return data
