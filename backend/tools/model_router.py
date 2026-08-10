"""
backend/tools/model_router.py — Per-agent model routing.

Maps each specialist agent to the right OpenAI model based on task complexity.
Security and quality use gpt-4o (high accuracy); tests and docs use gpt-4o-mini (cost).
"""
import os
from typing import Literal

AgentName = Literal["security", "quality", "tests", "docs", "orchestrator"]

# Default routing table — override with env vars for flexibility
_ROUTING_TABLE: dict[str, str] = {
    "security": "gpt-4o",       # High stakes — use best model
    "quality": "gpt-4o",        # Code quality needs nuanced reasoning
    "tests": "gpt-4o-mini",     # Test coverage checks are simpler
    "docs": "gpt-4o-mini",      # Doc quality checks are simpler
    "orchestrator": "gpt-4o",   # Aggregation & summary
}


def get_model_for_agent(agent_name: str) -> str:
    """Return the OpenAI model name to use for the given agent."""
    env_override = os.getenv(f"MODEL_{agent_name.upper()}")
    if env_override:
        return env_override
    return _ROUTING_TABLE.get(agent_name, "gpt-4o-mini")


def get_all_routes() -> dict[str, str]:
    """Return the full routing table with any env overrides applied."""
    return {name: get_model_for_agent(name) for name in _ROUTING_TABLE}
