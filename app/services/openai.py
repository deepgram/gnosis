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
    
    try:
        # Prepare search parameters - try without specifying a limit parameter since the API
        # is rejecting both 'limit' and 'top_k'
        search_params = {
            "query": query
        }
        
        # Add any additional parameters like filters
        if additional_params:
            if "filters" in additional_params:
                search_params["filter"] = additional_params["filters"]
        
        # Call OpenAI API to search the vector store
        response = client.vector_stores.search(
            vector_store_id=vector_store_id,
            **search_params
        )
        
        # Process the response
        results = []
        for item in response.data:
            # Extract content from the response
            content_text = ""
            if hasattr(item, "content") and item.content:
                for content_item in item.content:
                    if content_item.type == "text":
                        content_text += content_item.text + "\n"
            
            # Create metadata dictionary
            metadata = {}
            
            # Add metadata if available
            if hasattr(item, "metadata") and item.metadata:
                metadata = {
                    key: value for key, value in item.metadata.items()
                }
                
            # Add vector_store_id to metadata for tracking
            metadata["vector_store_id"] = vector_store_id
            
            # Add filename if available
            if hasattr(item, "filename"):
                metadata["filename"] = item.filename
            
            # Add file_id if available
            if hasattr(item, "file_id"):
                metadata["file_id"] = item.file_id
            
            # Create result object using the model
            result = VectorStoreResult(
                id=item.id,
                score=item.score,
                content=content_text.strip(),
                metadata=metadata
            )
                
            results.append(result)
            
            # If we have a limit set, only take that many results
            if limit and len(results) >= limit:
                break
        
        logger.info(f"Found {len(results)} results in vector store '{vector_store_id}'")
        return results
        
    except Exception as e:
        logger.error(f"Error in vector store search: {str(e)}")
        # Re-raise the exception so the caller can handle it
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
    
    # Gather all results
    try:
        all_results = await asyncio.gather(*tasks)
    except Exception as e:
        # Log and re-raise the exception
        logger.error(f"Vector search error: {str(e)}")
        raise
    
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