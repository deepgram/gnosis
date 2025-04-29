"""
Pydantic models for tool definitions and tool responses.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from pydantic import BaseModel, Field
import json


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
    Definition for a tool that can be called by a language model.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    required: Optional[List[str]] = None


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
    
    def model_dump(self):
        """Override model_dump to ensure serializable output"""
        return {
            "results": [result.model_dump() for result in self.results],
            "count": self.count
        }
    
    def __str__(self):
        """String representation for fallback serialization"""
        return f"VectorSearchResponse(count={self.count}, results={len(self.results)} items)"


class ToolError(BaseModel):
    """
    Error from a tool execution.
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