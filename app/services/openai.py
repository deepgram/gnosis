import logging
import asyncio
from typing import Dict, List, Any, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class VectorStoreResult(BaseModel):
    """Result from a vector store search."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def get_client() -> OpenAI:
    """
    Get an initialized OpenAI client.
    
    Returns:
        An initialized OpenAI client
    """
    return client


async def vector_store_search(
    query: str,
    vector_store_id: str,
    limit: int = 5,
    additional_params: Optional[Dict[str, Any]] = None
) -> List[VectorStoreResult]:
    """
    Search an OpenAI vector store using the provided query.
    
    Args:
        query: The search query
        vector_store_id: Identifier for the vector store to search
        limit: Maximum number of results to return
        additional_params: Additional parameters specific to the vector store
        
    Returns:
        List of search results with content and metadata
        
    Raises:
        Exception: If the vector store search fails
    """
    logger.info(f"Searching vector store '{vector_store_id}' with query: {query}")
    
    # Check OpenAI API key
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key is not set")
        raise ValueError("OpenAI API key is missing")
    
    try:
        # Use the correct method for OpenAI client vector store search
        # Prepare search parameters according to VectorStoreSearchParams type
        search_params = {
            "query": query,
            "max_num_results": min(limit, 50)  # Limit should be between 1-50
        }
        
        # Add additional parameters if provided (filters, ranking_options, rewrite_query)
        if additional_params:
            # Only include valid parameters for VectorStoreSearchParams
            valid_keys = ["filters", "ranking_options", "rewrite_query"]
            for key in valid_keys:
                if key in additional_params:
                    search_params[key] = additional_params[key]
            
        # Execute the search
        response = client.vector_stores.search(
            vector_store_id=vector_store_id,
            **search_params
        )
        
        # Process the response
        results = []
        
        # Check if response has the expected data attribute
        if not hasattr(response, "data"):
            logger.error("Response doesn't contain data attribute")
            raise ValueError("Invalid response structure from vector store search")
        
        # Process the results
        for item in response.data:
            # Build the content text based on response structure
            content_text = ""
            
            if hasattr(item, "content") and item.content:
                # Handle array of content items
                if isinstance(item.content, list):
                    for content_item in item.content:
                        if hasattr(content_item, "type") and content_item.type == "text":
                            content_text += getattr(content_item, "text", "") + "\n"
                # Handle direct text content            
                elif hasattr(item.content, "text"):
                    content_text = item.content.text
            # Try other common attributes
            elif hasattr(item, "text"):
                content_text = item.text
            
            # Extract metadata
            metadata = {}
            if hasattr(item, "metadata") and item.metadata:
                if isinstance(item.metadata, dict):
                    metadata = item.metadata
                else:
                    # Try to convert to dict if it's another object
                    metadata = {
                        key: getattr(item.metadata, key) 
                        for key in dir(item.metadata) 
                        if not key.startswith('_') and not callable(getattr(item.metadata, key))
                    }
                    
            # Add vector_store_id to metadata
            metadata["vector_store_id"] = vector_store_id
            
            # Extract file info if available
            if hasattr(item, "filename"):
                metadata["filename"] = item.filename
            if hasattr(item, "file_id"):
                metadata["file_id"] = item.file_id
            
            # Create result object
            result = VectorStoreResult(
                id=getattr(item, "id", "unknown"),
                score=getattr(item, "score", 0.0),
                content=content_text.strip(),
                metadata=metadata
            )
            
            results.append(result)
        
        logger.info(f"Found {len(results)} results in vector store search")
        return results
        
    except Exception as e:
        logger.error(f"Error in vector store search: {str(e)}")
        # Re-raise the exception so caller can handle it properly
        raise


async def perform_vector_search(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Perform vector search across multiple vector stores for RAG.
    
    Args:
        query: The search query
        limit: Maximum number of results to return per store
        
    Returns:
        Combined list of search results
        
    Raises:
        Exception: If the vector search fails
    """
    # Dictionary of vector store IDs to search
    vector_stores = {
        "vs_67ff646e0558819189933696b5b165b1": "Documentation"
    }
    
    # Search all vector stores concurrently
    tasks = [
        vector_store_search(query, store_id, limit)
        for store_id in vector_stores.keys()
    ]
    
    # Gather all results - let exceptions propagate
    all_results = await asyncio.gather(*tasks)
    
    # Flatten results and sort by score
    flattened_results = [
        result.model_dump() for sublist in all_results for result in sublist
    ]
    
    # Sort by score (descending)
    sorted_results = sorted(
        flattened_results,
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    
    # Return top results across all stores
    return sorted_results[:limit]


def get_vector_store_id_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Extract the vector store ID from result metadata"""
    return metadata.get("vector_store_id") 