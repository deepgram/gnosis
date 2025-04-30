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
    type: Literal["function"] = "function"
    function: Dict[str, Any] = Field(...)


class ContentItem(BaseModel):
    """
    A content item in a vector search result.
    """
    type: str
    text: str


class VectorSearchDataItem(BaseModel):
    """
    An item in the data array of a vector search response.
    """
    file_id: Optional[str] = None
    filename: Optional[str] = None
    score: Optional[float] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    content: List[ContentItem] = Field(default_factory=list)
    
    # For backward compatibility with original API responses
    metadata: Optional[Dict[str, Any]] = None
    vector_distance: Optional[float] = None
    
    @property
    def text(self) -> str:
        """Get all text content concatenated."""
        return " ".join([item.text for item in self.content if item.type == "text"])


class VectorSearchResponse(BaseModel):
    """
    Response from a vector search tool.
    """
    object: Optional[str] = None
    search_query: Optional[str] = None
    data: List[VectorSearchDataItem] = Field(default_factory=list)
    has_more: Optional[bool] = None
    next_page: Optional[str] = None
    
    # For backward compatibility with original API
    matches: Optional[List[VectorSearchDataItem]] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    
    def model_dump(self):
        """Override model_dump to ensure serializable output"""
        result = {}
        if self.object:
            result["object"] = self.object
        if self.search_query:
            result["search_query"] = self.search_query
        if self.data:
            result["data"] = [item.model_dump() for item in self.data]
        if self.has_more is not None:
            result["has_more"] = self.has_more
        if self.next_page:
            result["next_page"] = self.next_page
            
        # Include backward compatibility fields if present
        if self.matches:
            result["matches"] = [match.model_dump() for match in self.matches]
        if self.model:
            result["model"] = self.model
        if self.usage:
            result["usage"] = self.usage
        return result
    
    def __str__(self):
        """String representation for fallback serialization"""
        count = len(self.data) if self.data else len(self.matches) if self.matches else 0
        return f"VectorSearchResponse(count={count} items)"


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