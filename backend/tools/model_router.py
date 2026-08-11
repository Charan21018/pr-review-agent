"""
backend/tools/model_router.py — Per-agent model routing.

Maps each specialist agent to the right Gemini model based on task complexity.
Defaults all agents to gemini-2.5-flash: gemini-2.5-pro returns 404 ("no
longer available to new users") on free-tier API keys, so it is not a safe
default here. If your GEMINI_API_KEY has pro-tier billing enabled, override
per agent with MODEL_SECURITY / MODEL_QUALITY / MODEL_TESTS / MODEL_DOCS /
MODEL_ORCHESTRATOR env vars.
"""
import os
from typing import Literal

AgentName = Literal["security", "quality", "tests", "docs", "orchestrator"]

# Default routing table — override with env vars for flexibility
_ROUTING_TABLE: dict[str, str] = {
    "security": "gemini-2.5-flash",
    "quality": "gemini-2.5-flash",
    "tests": "gemini-2.5-flash",
    "docs": "gemini-2.5-flash",
    "orchestrator": "gemini-2.5-flash",
}


def get_model_for_agent(agent_name: str) -> str:
    """Return the Gemini model name to use for the given agent."""
    env_override = os.getenv(f"MODEL_{agent_name.upper()}")
    if env_override:
        return env_override
    return _ROUTING_TABLE.get(agent_name, "gemini-2.5-flash")


def get_all_routes() -> dict[str, str]:
    """Return the full routing table with any env overrides applied."""
    return {name: get_model_for_agent(name) for name in _ROUTING_TABLE}
