import logging
from typing import Dict, List, Any, Optional

from openai import OpenAI
from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


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
) -> List[Dict[str, Any]]:
    """
    Search an OpenAI vector store using the provided query.
    
    Args:
        query: The search query
        vector_store_id: Identifier for the vector store to search
        limit: Maximum number of results to return
        additional_params: Additional parameters specific to the vector store
        
    Returns:
        List of search results with content and metadata
    """
    logger.info(f"Searching vector store '{vector_store_id}' with query: {query}")
    
    try:
        # Prepare search parameters
        search_params = {
            "query": query,
            "limit": limit
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
            
            # Create result object
            result = {
                "id": item.id,
                "score": item.score,
                "content": content_text.strip(),
                "metadata": {}
            }
            
            # Add metadata if available
            if hasattr(item, "metadata") and item.metadata:
                result["metadata"] = {
                    key: value for key, value in item.metadata.items()
                }
                
                # Add vector_store_id to metadata for tracking
                result["metadata"]["vector_store_id"] = vector_store_id
            
            # Add filename if available
            if hasattr(item, "filename"):
                result["metadata"]["filename"] = item.filename
            
            # Add file_id if available
            if hasattr(item, "file_id"):
                result["metadata"]["file_id"] = item.file_id
                
            results.append(result)
        
        logger.info(f"Found {len(results)} results in vector store '{vector_store_id}'")
        return results
        
    except Exception as e:
        logger.error(f"Error in vector store search: {str(e)}")
        return [] 