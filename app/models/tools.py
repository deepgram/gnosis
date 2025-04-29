"""
Pydantic models for tool definitions and tool responses.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """
    Definition of a parameter for a tool.
    """
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolParametersSchema(BaseModel):
    """
    JSON Schema for tool parameters.
    """
    type: Literal["object"] = "object"
    properties: Dict[str, ToolParameter]
    required: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """
    Definition of a tool that can be used by the LLM.
    """
    type: Literal["function"] = "function"
    function: Dict[str, Any] = Field(...)


class VectorSearchResult(BaseModel):
    """
    Result from a vector search.
    """
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: Optional[float] = None


class VectorSearchResponse(BaseModel):
    """
    Response from a vector search tool.
    """
    results: List[VectorSearchResult]
    count: int


class ToolError(BaseModel):
    """
    Error response from a tool.
    """
    error: str


# Union type for any tool response
ToolResponse = Union[VectorSearchResponse, ToolError, Dict[str, Any]]


class ToolRegistry(BaseModel):
    """
    Registry for tools and their definitions.
    """
    tools: Dict[str, Any] = Field(default_factory=dict)
    tool_definitions: Dict[str, ToolDefinition] = Field(default_factory=dict) 