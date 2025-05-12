"""
Pydantic models for OpenAI Chat Completions API.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class VectorStoreSearchRequest(BaseModel):
    """Request body for vector store search API."""

    query: str
    max_num_results: Optional[int] = 10
    ranking_options: Optional[Dict[str, Any]] = None
    rewrite_query: Optional[bool] = False


class VectorStoreItem(BaseModel):
    """Item in a vector store."""

    file_id: str
    filename: str
    score: float
    attributes: Dict[str, Any]
    content: List[Dict[str, Any]]


class VectorStoreSearchResponse(BaseModel):
    """Response body for vector store search API."""

    object: str
    search_query: str
    data: List[VectorStoreItem]
    has_more: bool
    next_page: Optional[str] = None
