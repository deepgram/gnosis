from typing import Any, Callable, Dict, Awaitable

# Dictionary of registered tools
# Key is the tool name, value is an async function that takes arguments and returns a result
tools: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}


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


# Register built-in tools
@register_tool("search_knowledge_base")
async def search_knowledge_base(arguments: Dict[str, Any]) -> Any:
    """
    Search the knowledge base for information.
    """
    query = arguments.get("query", "")
    
    # In a real implementation, this would search a knowledge base
    return {
        "results": [
            {
                "title": f"Result for '{query}'",
                "content": f"This is a sample result for the query '{query}'.",
                "score": 0.95
            }
        ]
    } 