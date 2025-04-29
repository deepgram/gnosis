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
        # The OpenAI client might be using the wrong path; use a direct request instead
        import httpx
        
        search_url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/search"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        search_data = {
            "query": query
        }
        
        logger.info(f"Making direct request to {search_url}")
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                search_url,
                headers=headers,
                json=search_data
            )
            
            # Check if the response was successful
            if response.status_code != 200:
                logger.error(f"Vector store search failed with status {response.status_code}: {response.text}")
                raise ValueError(f"Vector store search failed with status {response.status_code}")
            
            # Parse the response
            response_data = response.json()
            
        # Process the response
        results = []
        
        # Check if response has the expected data attribute
        if "data" not in response_data:
            logger.error("Response doesn't contain data attribute")
            raise ValueError("Invalid response structure from vector store search")
        
        # Process the results
        for item in response_data["data"]:
            # Build the content text based on response structure
            content_text = ""
            
            if "content" in item and item["content"]:
                # Handle array of content items
                if isinstance(item["content"], list):
                    for content_item in item["content"]:
                        if content_item.get("type") == "text":
                            content_text += content_item.get("text", "") + "\n"
                # Handle direct text content            
                elif isinstance(item["content"], dict) and "text" in item["content"]:
                    content_text = item["content"]["text"]
            # Try other common attributes
            elif "text" in item:
                content_text = item["text"]
            
            # Extract metadata
            metadata = {}
            if "metadata" in item and item["metadata"]:
                metadata = item["metadata"].copy()
                    
            # Add vector_store_id to metadata
            metadata["vector_store_id"] = vector_store_id
            
            # Extract file info if available
            if "filename" in item:
                metadata["filename"] = item["filename"]
            if "file_id" in item:
                metadata["file_id"] = item["file_id"]
            
            # Create result object
            result = VectorStoreResult(
                id=item.get("id", "unknown"),
                score=item.get("score", 0.0),
                content=content_text.strip(),
                metadata=metadata
            )
            
            results.append(result)
            
            # Limit results if needed
            if limit and len(results) >= limit:
                break
        
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