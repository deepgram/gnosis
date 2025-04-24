from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MCPCapability(BaseModel):
    """Capability in the MCP protocol"""
    supported: bool
    config: Optional[Dict[str, Any]] = None


class MCPServerCapabilities(BaseModel):
    """Server capabilities in the MCP protocol"""
    resources: MCPCapability
    tools: MCPCapability
    prompts: MCPCapability
    protocol: Dict[str, Any]


class MCPClientCapabilities(BaseModel):
    """Client capabilities in the MCP protocol"""
    sampling: Optional[MCPCapability] = None
    protocol: Dict[str, Any]


class MCPResourceMetadata(BaseModel):
    """Metadata for an MCP resource"""
    source: Optional[str] = None
    score: Optional[float] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    tags: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None


class MCPResource(BaseModel):
    """Resource in the MCP protocol"""
    id: str
    type: str
    content: str
    metadata: Optional[MCPResourceMetadata] = None


class MCPToolParameter(BaseModel):
    """Parameter for an MCP tool"""
    type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """Tool in the MCP protocol"""
    name: str
    description: Optional[str] = None
    parameters: MCPToolParameter


class MCPRequest(BaseModel):
    """Generic JSON-RPC request for MCP"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Generic JSON-RPC response for MCP"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None 