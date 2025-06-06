from typing import Any, Callable, Dict, Awaitable, List, Optional
import structlog
import uuid
import json

from app.models.registry import ToolRegistry, RegistryItem
from app.models.chat import ToolCall, ToolCallFunction

# Get a logger for this module
log = structlog.get_logger()

# Create the registry using the Pydantic model
registry = ToolRegistry()

# A comprehensive tool registry that contains both implementations and definitions
tool_registry = registry.registry


# Compatibility layer for existing code (simulating the old 'tools' dict)
class ToolsDict(dict):
    def __getitem__(self, key):
        return get_tool_implementation(key)

    def get(self, key, default=None):
        impl = get_tool_implementation(key)
        return impl if impl is not None else default

    def __contains__(self, key):
        return get_tool_implementation(key) is not None


# Create the tools compatibility object
tools = ToolsDict()


def register_tool(
    name: str,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    scope: str = "public",
):
    """
    Enhanced decorator to register both a function and its schema definition.

    Args:
        name: The name of the tool
        description: A description of what the tool does
        parameters: The JSON Schema for the tool's parameters
        scope: The scope of the tool (public, private, or internal)
    Returns:
        Decorator function that registers the decorated function
    """

    def decorator(
        func: Callable[[Dict[str, Any]], Awaitable[Any]],
    ) -> Callable[[Dict[str, Any]], Awaitable[Any]]:
        # Create or update the tool entry in the registry
        if name not in tool_registry:
            tool_registry[name] = RegistryItem(scope=scope)

        # Register the implementation
        tool_registry[name].implementation = func
        log.debug(f"Registered tool implementation: {name}")

        # If description and parameters provided, register the definition
        if description and parameters:
            # Create a ToolCall function with extra metadata in model_extra
            function_data = {
                "name": name,
                "arguments": json.dumps(
                    {"description": description, "parameters": parameters}
                ),
            }

            tool_call = ToolCall(
                id=f"def_{uuid.uuid4()}",
                type="function",
                function=ToolCallFunction(**function_data),
            )

            # Register the definition
            tool_registry[name].definition = tool_call
            log.debug(f"Registered tool definition: {name}")

        return func

    return decorator


# Helper functions to access the registry


def get_tool_implementation(name: str) -> Optional[Callable]:
    """Get the implementation function for a tool."""
    return registry.get_implementation(name)


def get_tool_definition(name: str) -> Optional[Dict[str, Any]]:
    """Get the definition for a tool."""
    definition = registry.get_definition(name)
    if definition:
        return definition.model_dump()
    return None


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """Get all tool definitions."""
    return [tool_def.model_dump() for tool_def in registry.get_all_definitions()]


async def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a tool by name with the given arguments."""
    implementation = get_tool_implementation(name)
    if implementation:
        log.debug(f"Executing tool: {name}")
        return await implementation(arguments)
    log.warning(f"Tool implementation not found: {name}")
    return {"error": f"Tool '{name}' not found"}


def create_tool_call(name: str, arguments: str) -> ToolCall:
    """Create a ToolCall object for the given tool name and arguments."""
    return ToolCall(
        id=f"call_{uuid.uuid4()}",
        type="function",
        function=ToolCallFunction(name=name, arguments=arguments),
    )
