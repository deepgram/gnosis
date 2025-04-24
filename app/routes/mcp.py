import json
from typing import Any, Dict, List, Optional, Union

from litestar import Router, Request, WebSocket, get, post, websocket
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_400_BAD_REQUEST

from app.config import settings
from app.models.mcp import MCPRequest, MCPResponse, MCPCapability, MCPResource, MCPTool


@websocket("/mcp")
async def mcp_websocket(websocket: WebSocket) -> None:
    """
    Handle MCP WebSocket connections.
    """
    if not settings.MCP_ENABLED:
        await websocket.close(1000, "MCP is disabled")
        return

    await websocket.accept()
    
    # Initialize connection state
    connection_id = str(id(websocket))
    capabilities = get_server_capabilities()
    
    try:
        # Send server capabilities in the handshake
        await websocket.send_json({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 0,
            "params": {
                "capabilities": capabilities
            }
        })
        
        # Process messages from the client
        while True:
            message = await websocket.receive_text()
            
            try:
                rpc_request = json.loads(message)
                
                # Basic validation
                if "jsonrpc" not in rpc_request or rpc_request["jsonrpc"] != "2.0":
                    raise ValueError("Invalid JSON-RPC message")
                
                # Process the RPC request
                response = await process_mcp_request(rpc_request, connection_id)
                
                # Send the response
                await websocket.send_json(response)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    },
                    "id": None
                })
            except Exception as e:
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": rpc_request.get("id", None) if "rpc_request" in locals() else None
                })
    
    except Exception as e:
        # Connection error or client disconnected
        pass
    finally:
        # Clean up connection resources
        pass


async def process_mcp_request(request: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
    """
    Process an MCP JSON-RPC request.
    """
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", None)
    
    # Handle different method types
    if method == "initialize":
        # Client initialization
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "capabilities": get_server_capabilities()
            }
        }
    
    elif method == "shutdown":
        # Client shutting down
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": None
        }
    
    elif method == "resources/get":
        # Get resources based on query
        resources = await get_resources(params.get("query", ""), connection_id)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": resources
            }
        }
    
    elif method == "tools/list":
        # List available tools
        tools = await list_tools(connection_id)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    
    elif method == "tools/execute":
        # Execute a tool
        result = await execute_tool(
            params.get("name", ""),
            params.get("arguments", {}),
            connection_id
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    else:
        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def get_server_capabilities() -> Dict[str, Any]:
    """
    Get the server capabilities for MCP.
    """
    return {
        "resources": {
            "supported": True,
        },
        "tools": {
            "supported": True,
        },
        "prompts": {
            "supported": False,
        },
        "protocol": {
            "version": "2025-03-26",
        }
    }


async def get_resources(query: str, connection_id: str) -> List[Dict[str, Any]]:
    """
    Get resources based on the query.
    """
    # In a real implementation, this would search knowledge bases, databases, etc.
    # based on the query and return relevant resources
    return [
        {
            "id": "demo-resource-1",
            "type": "text",
            "content": f"This is a demo resource for query: {query}",
            "metadata": {
                "source": "gnosis-demo",
                "score": 0.95
            }
        }
    ]


async def list_tools(connection_id: str) -> List[Dict[str, Any]]:
    """
    List available tools for the MCP client.
    """
    # In a real implementation, this would be loaded from a registry
    return [
        {
            "name": "search_knowledge_base",
            "description": "Search the knowledge base for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    ]


async def execute_tool(name: str, arguments: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
    """
    Execute a tool with the given arguments.
    """
    # In a real implementation, this would dispatch to registered tool handlers
    if name == "search_knowledge_base":
        query = arguments.get("query", "")
        # Perform the search
        return {
            "status": "success",
            "result": f"Search results for '{query}': Sample result 1, Sample result 2"
        }
    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {name}"
        }


mcp_router = Router(
    path="/mcp",
    route_handlers=[
        websocket,
    ],
    tags=["Model Context Protocol"],
) 