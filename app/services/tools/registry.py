from typing import Any, Callable, Dict, Awaitable, List, Optional

# Dictionary of registered tools
# Key is the tool name, value is an async function that takes arguments and returns a result
tools: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}

# Dictionary of tool definitions with metadata
# This will be exposed to the OpenAI API
tool_definitions: Dict[str, Dict[str, Any]] = {}


def register_tool(name: str) -> Callable[[Callable], Callable]:
    """
    Decorator to register a function as a tool handler.
    
    Usage:
    
    @register_tool("search_knowledge_base")
    async def search_knowledge_base(arguments: Dict[str, Any]) -> Any:
        # Implementation
        pass
    """
    def decorator(func: Callable[[Dict[str, Any]], Awaitable[Any]]) -> Callable[[Dict[str, Any]], Awaitable[Any]]:
        tools[name] = func
        return func
    return decorator


def register_tool_definition(name: str, description: str, parameters: Dict[str, Any]) -> None:
    """
    Register a tool definition that will be exposed to the OpenAI API.
    
    Args:
        name: The name of the tool
        description: A description of what the tool does
        parameters: The JSON Schema for the tool's parameters
    """
    tool_definitions[name] = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    }


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all registered tool definitions.
    
    Returns:
        A list of tool definitions in the format expected by OpenAI API
    """
    return list(tool_definitions.values())


def get_tool_definition(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific tool definition by name.
    
    Args:
        name: The name of the tool
        
    Returns:
        The tool definition or None if not found
    """
    return tool_definitions.get(name)