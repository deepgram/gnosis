"""
Pydantic models for tool definitions and tool responses.
"""

from typing import Any, Dict, List, Literal, Optional, Union
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
    Matches the OpenAI vector store API response format exactly.
    """
    file_id: str
    filename: str
    score: float
    attributes: Dict[str, Any] = Field(default_factory=dict)
    content: List[ContentItem]
    
    @property
    def text(self) -> str:
        """Get all text content concatenated."""
        return " ".join([item.text for item in self.content if item.type == "text"])
    
    def model_dump(self, **kwargs):
        """Override model_dump to ensure serializable output"""
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "score": self.score,
            "attributes": self.attributes,
            "content": [
                {"type": item.type, "text": item.text}
                for item in self.content
            ]
        }


class VectorSearchResponse(BaseModel):
    """
    Response from a vector search tool.
    Follows the exact format of OpenAI's vector store API.
    """
    object: str = "vector_store.search_results.page"
    search_query: str
    data: List[VectorSearchDataItem]
    has_more: bool = False
    next_page: Optional[str] = None
    
    def model_dump(self):
        """Override model_dump to ensure serializable output"""
        result = {
            "object": self.object,
            "search_query": self.search_query,
            "data": [item.model_dump() for item in self.data],
            "has_more": self.has_more
        }
        
        if self.next_page:
            result["next_page"] = self.next_page
            
        return result
    
    def __str__(self):
        """String representation for fallback serialization"""
        return f"VectorSearchResponse(query='{self.search_query}', items={len(self.data)})"


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
    
    The registry is now a unified structure where each tool has both
    an implementation and a definition, allowing for simpler registration
    and access.
    """
    registry: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    def get_implementation(self, name: str) -> Optional[Any]:
        """Get a tool implementation by name."""
        return self.registry.get(name, {}).get("implementation")
    
    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        definition_dict = self.registry.get(name, {}).get("definition")
        if definition_dict:
            return ToolDefinition(**definition_dict)
        return None
    
    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions."""
        return [entry["definition"] for entry in self.registry.values() 
                if entry.get("definition") is not None] 