import json
import logging
from typing import Any, Dict, List, Optional
import os

from openai import OpenAI

from app.config import settings
from app.services.tools.registry import register_tool

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize OpenAI client using API key from settings
client = OpenAI(api_key=settings.OPENAI_API_KEY)


@register_tool("vector_search")
async def vector_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search an OpenAI Vector Store and return the relevant documents.
    
    Arguments:
        vector_store_id: The ID of the OpenAI Vector Store
        query: The search query
        max_results: (Optional) Maximum number of results to return, defaults to 5
        filter: (Optional) Filter to apply to the search
        
    Returns:
        Dictionary containing the search results and metadata
    """
    logger.info(f"Performing vector search with arguments: {arguments}")
    
    # Extract arguments
    vector_store_id = arguments.get("vector_store_id")
    query = arguments.get("query")
    max_results = arguments.get("max_results", 5)
    filter_param = arguments.get("filter")
    
    # Validate required arguments
    if not vector_store_id:
        logger.error("Missing required argument: vector_store_id")
        return {"error": "Missing required argument: vector_store_id"}
    
    if not query:
        logger.error("Missing required argument: query")
        return {"error": "Missing required argument: query"}
    
    try:
        # Perform the vector search
        logger.info(f"Searching vector store {vector_store_id} for: '{query}'")
        
        # Prepare search parameters
        search_params = {
            "query": query,
            "limit": max_results,
        }
        
        # Add filter if provided
        if filter_param:
            search_params["filter"] = filter_param
        
        # Call OpenAI API
        response = client.vector_stores.search(
            vector_store_id=vector_store_id,
            **search_params
        )
        
        # Process and format the results
        results = format_vector_search_results(response)
        
        logger.info(f"Vector search successful, found {len(results)} results")
        return {
            "status": "success",
            "results_count": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


def format_vector_search_results(response: Any) -> List[Dict[str, Any]]:
    """
    Format the results from a vector store search into a structured format.
    
    Args:
        response: The raw response from the OpenAI vector store search
    
    Returns:
        A list of formatted document entries
    """
    formatted_results = []
    
    for item in response.data:
        # Extract content
        content_text = ""
        if hasattr(item, "content") and item.content:
            for content_item in item.content:
                if content_item.type == "text":
                    content_text += content_item.text + "\n"
        
        # Create formatted result entry
        result = {
            "id": item.id,
            "score": item.score,
            "file_id": getattr(item, "file_id", None),
            "metadata": json.loads(json.dumps(getattr(item, "metadata", {}))),
            "content": content_text.strip()
        }
        
        # Add filename if available
        if hasattr(item, "filename"):
            result["filename"] = item.filename
        
        formatted_results.append(result)
    
    return formatted_results


def get_vector_store_id_from_metadata(metadata_path: Optional[str] = None) -> str:
    """
    Get the vector store ID from a metadata file.
    
    Args:
        metadata_path: Path to the metadata file, defaults to '.bin/vectorstore_metadata.json'
    
    Returns:
        The vector store ID
    
    Raises:
        FileNotFoundError: If the metadata file doesn't exist
        ValueError: If the vector store ID is not found in the metadata
    """
    import json
    from pathlib import Path
    
    # Use default path if none provided
    if not metadata_path:
        metadata_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".bin", 
            "vectorstore_metadata.json"
        )
    
    # Check if file exists
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Vector store metadata file not found: {metadata_path}")
    
    # Read and parse the metadata file
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Extract vector store ID
    vector_store_id = metadata.get("vectorStoreId")
    if not vector_store_id:
        raise ValueError("Vector store ID not found in metadata file")
    
    return vector_store_id 