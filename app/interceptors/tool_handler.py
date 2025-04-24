import json
from typing import Any, Dict, List

from app.services.tools import registry


async def process_tool_calls(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process tool calls in the response from OpenAI.
    
    This function intercepts tool calls, executes them, and injects the results
    back into the conversation.
    """
    if "choices" not in response_data or not response_data["choices"]:
        return response_data
    
    choice = response_data["choices"][0]
    if "message" not in choice or "tool_calls" not in choice["message"]:
        return response_data
    
    tool_calls = choice["message"]["tool_calls"]
    
    # Process each tool call
    tool_results = []
    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id", "")
        function = tool_call.get("function", {})
        name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")
        
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}
        
        # Execute the tool
        result = await execute_tool(name, arguments)
        
        # Add the result to our list
        tool_results.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        })
    
    # Add the tool results to the response
    if tool_results:
        # Check if there's already a messages array
        if "messages" not in response_data:
            response_data["messages"] = []
        
        # Add the original assistant message if it's not already there
        if not any(msg.get("role") == "assistant" for msg in response_data["messages"]):
            response_data["messages"].append({
                "role": "assistant",
                "content": choice["message"].get("content", ""),
                "tool_calls": tool_calls
            })
        
        # Add the tool results
        response_data["messages"].extend(tool_results)
    
    return response_data


async def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """
    Execute a tool by name with the given arguments.
    
    This delegates to the tool registry to find and execute the appropriate tool.
    """
    # Check if we have a registered handler for this tool
    if name in registry.tools:
        try:
            return await registry.tools[name](arguments)
        except Exception as e:
            return {
                "error": f"Error executing tool {name}: {str(e)}"
            }
    else:
        # We don't have a handler for this tool
        return {
            "error": f"Unknown tool: {name}"
        } 