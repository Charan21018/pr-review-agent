"""backend/tools/tool_registry.py — Tool catalog registry.

Registers capabilities (tools) available to specialized agents during execution.
Each tool maps to a callable, descriptor, and required capability scope.
"""
from typing import Callable, Dict, Any, List, Optional
from pydantic import BaseModel

class ToolDescriptor(BaseModel):
    name: str
    description: str
    arguments_schema: Dict[str, Any]
    required_scope: str  # e.g., 'read_only', 'sandbox_exec', 'network_access'

class ToolRegistry:
    """Registry that holds tool definitions and verifies caller capabilities."""

    def __init__(self):
        self._tools: Dict[str, ToolDescriptor] = {}
        self._callables: Dict[str, Callable] = {}

    def register(self, name: str, description: str, arguments_schema: Dict[str, Any], required_scope: str) -> Callable:
        """Decorator to register a function as a tool."""
        def decorator(func: Callable) -> Callable:
            self._tools[name] = ToolDescriptor(
                name=name,
                description=description,
                arguments_schema=arguments_schema,
                required_scope=required_scope
            )
            self._callables[name] = func
            return func
        return decorator

    def get_tool_descriptor(self, name: str) -> Optional[ToolDescriptor]:
        return self._tools.get(name)

    def get_callable(self, name: str) -> Optional[Callable]:
        return self._callables.get(name)

    def list_tools(self) -> List[ToolDescriptor]:
        return list(self._tools.values())

    async def execute(self, name: str, scope_verifier: Callable[[str], bool], **kwargs) -> Any:
        """Executes a registered tool if the agent's capability scope is valid."""
        descriptor = self.get_tool_descriptor(name)
        if not descriptor:
            raise KeyError(f"Tool '{name}' not found in registry.")

        if not scope_verifier(descriptor.required_scope):
            from backend.core.exceptions import ToolPermissionError
            raise ToolPermissionError(
                f"Execution denied: Tool '{name}' requires scope '{descriptor.required_scope}' which is not permitted."
            )

        func = self.get_callable(name)
        if not func:
            raise RuntimeError(f"Callable for tool '{name}' is missing.")

        # Execute
        import inspect
        if inspect.iscoroutinefunction(func):
            return await func(**kwargs)
        return func(**kwargs)

# Global singleton tool registry
tool_registry = ToolRegistry()
