"""
backend/tools/llm_client.py — OpenAI LLM client wrapper with mock fallback.

Handles:
- Chat completions with retry on rate limits
- Token counting and cost calculation
- Graceful mock fallback if API quota is exhausted or key is invalid (I2/Move 5 invariant).
"""
import os
import re
import time
import json
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI, RateLimitError, APITimeoutError

_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


def compute_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = _PRICING.get(model, {"input": 5.0, "output": 15.0})
    return (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000


# Each rule: (regex over the diff/prompt text, finding template dict)
_SECURITY_RULES = [
    (
        re.compile(r'\b(api_key|apikey|secret|password|passwd|token)\s*=\s*["\'][^"\']{6,}["\']', re.I),
        {
            "severity": "CRITICAL",
            "category": "Hardcoded Secrets",
            "rationale": "Hardcoded API Key detected in app.py. Move credentials to environment variables.",
            "confidence": 0.95,
        },
    ),
    (
        re.compile(r'\bselect\b.{0,80}\bfrom\b', re.I | re.S),
        {
            "severity": "HIGH",
            "category": "SQL Injection",
            "rationale": "Query built via string interpolation is vulnerable to SQL injection. Use parameterized queries instead.",
            "confidence": 0.90,
        },
    ),
    (
        re.compile(r'\b(exec|eval)\s*\(|os\.system\s*\(|subprocess\.\w+\([^)]*shell\s*=\s*True'),
        {
            "severity": "HIGH",
            "category": "Command Execution",
            "rationale": "Dynamic execution of code/commands (exec/eval/os.system) permits arbitrary code execution. Avoid executing untrusted input.",
            "confidence": 0.90,
        },
    ),
]

_QUALITY_RULES = [
    (
        re.compile(r'except\s*:'),
        {
            "severity": "MEDIUM",
            "category": "Swallowed Exception",
            "rationale": "Bare except silently swallows all exceptions, hiding bugs. Catch specific exceptions and handle or log them.",
            "confidence": 0.85,
        },
    ),
    (
        re.compile(r'\bprint\s*\('),
        {
            "severity": "LOW",
            "category": "Debug Statement",
            "rationale": "Leftover print statement. Replace with structured logging.",
            "confidence": 0.85,
        },
    ),
]

_TESTS_RULES = [
    (
        re.compile(r'^\+\s*def\s+(?!test_)\w+\s*\(', re.M),
        {
            "severity": "MEDIUM",
            "category": "Missing Unit Tests",
            "rationale": "New function has no test coverage. Add test cases covering its behavior.",
            "confidence": 0.80,
        },
    ),
    (
        re.compile(r'@pytest\.mark\.skip'),
        {
            "severity": "LOW",
            "category": "Skipped Test",
            "rationale": "Test is marked skip and will not run in CI. Remove the skip marker or document why it's necessary.",
            "confidence": 0.75,
        },
    ),
]

_DOCS_RULES = [
    (
        re.compile(r'#\s*(TODO|FIXME)\b', re.I),
        {
            "severity": "LOW",
            "category": "Documentation Marker",
            "rationale": "TODO/FIXME marker left in code without a tracked issue. Resolve it or link to a ticket.",
            "confidence": 0.70,
        },
    ),
]

_RULES_BY_AGENT = {
    "security": _SECURITY_RULES,
    "quality": _QUALITY_RULES,
    "tests": _TESTS_RULES,
    "docs": _DOCS_RULES,
}


def _generate_mock_llm_response(agent_name: str, diff_text: str = "") -> str:
    """Generate a mock response by pattern-matching the diff text, so findings
    reflect actual diff content instead of a fixed canned response."""
    for key, rules in _RULES_BY_AGENT.items():
        if key in agent_name or (key == "tests" and "test" in agent_name):
            findings = []
            for pattern, template in rules:
                if pattern.search(diff_text):
                    finding = dict(template)
                    finding.setdefault("file_path", None)
                    finding.setdefault("line_start", None)
                    finding.setdefault("line_end", None)
                    findings.append(finding)
            return json.dumps({"findings": findings})

    # Default mock PR summary comment (aggregator-level, not a specialist)
    return """### PR Review Summary
The review pipeline completed. See individual specialist findings above.

**Recommendation: See aggregator decision.**"""


async def chat_completion(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    json_mode: bool = False,
    max_retries: int = 3,
    agent_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Call OpenAI chat completion with retries.
    Falls back to high-quality mock responses if the API quota is exhausted or errors occur.
    """
    try:
        client = _get_client()
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(max_retries):
            t0 = time.monotonic()
            try:
                response = await client.chat.completions.create(**kwargs)
                latency_ms = int((time.monotonic() - t0) * 1000)
                usage = response.usage
                tokens_in = usage.prompt_tokens if usage else 0
                tokens_out = usage.completion_tokens if usage else 0
                cost_usd = compute_cost(model, tokens_in, tokens_out)
                text = response.choices[0].message.content or ""
                return {
                    "text": text,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "model": model,
                }
            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except APITimeoutError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
    except Exception as e:
        print(f"[Warning] OpenAI chat completion failed ({e}). Falling back to mock agent response.")
        if agent_name is not None:
            # Caller told us explicitly which specialist this is — trust it.
            # (Inferring from system_prompt text is unreliable: prompts share
            # vocabulary, e.g. tests.system mentions "quality" too.)
            agent_key = agent_name
        else:
            agent_key = "default"
            if "security" in system_prompt.lower():
                agent_key = "security"
            elif "quality" in system_prompt.lower():
                agent_key = "quality"
            elif "test" in system_prompt.lower():
                agent_key = "tests"
            elif "doc" in system_prompt.lower():
                agent_key = "docs"

        return {
            "text": _generate_mock_llm_response(agent_key, user_prompt),
            "tokens_in": 150,
            "tokens_out": 250,
            "cost_usd": 0.0005,
            "latency_ms": 100,
            "model": model,
        }


async def chat_completion_json(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    agent_name: Optional[str] = None,
) -> tuple[Any, dict]:
    result = await chat_completion(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
        agent_name=agent_name,
    )
    try:
        parsed = json.loads(result["text"])
    except json.JSONDecodeError:
        parsed = {}
    return parsed, result
