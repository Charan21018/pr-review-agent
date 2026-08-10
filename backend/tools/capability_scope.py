"""backend/tools/capability_scope.py — Tool scope enforcement.

Validates that an agent has the required permission/scope to invoke a given tool.
Implements security controls preventing docs agents from executing shell code, etc.
"""
from typing import Dict, Set
from backend.models.enums import AgentType
from backend.core.exceptions import ToolPermissionError

# Define allowed scopes per AgentType
AGENT_ALLOWED_SCOPES: Dict[AgentType, Set[str]] = {
    AgentType.SECURITY: {"read_only", "sandbox_exec"},
    AgentType.QUALITY: {"read_only"},
    AgentType.TESTS: {"read_only", "sandbox_exec"},
    AgentType.DOCS: {"read_only"},
    AgentType.AGGREGATOR: {"read_only"},
    AgentType.SYSTEM: {"read_only", "sandbox_exec", "network_access"},
}

class CapabilityScopeVerifier:
    """Checks whether a given agent type is allowed to access a specific capability/scope."""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type

    def has_scope(self, required_scope: str) -> bool:
        """Returns True if the agent's scopes include the required scope."""
        allowed = AGENT_ALLOWED_SCOPES.get(self.agent_type, set())
        return required_scope in allowed

    def verify(self, required_scope: str) -> None:
        """Raises ToolPermissionError if the agent is not authorized."""
        if not self.has_scope(required_scope):
            raise ToolPermissionError(
                f"Agent '{self.agent_type.value}' is not authorized to use capabilities requiring '{required_scope}' scope."
            )
