import json
import logging
import httpx
from typing import Dict, List, Any, Optional, Union

from app.config import settings
from app.services.tools.registry import register_tool
from app.models.tools import VectorSearchResponse, VectorSearchDataItem, ContentItem, ToolError

# Get a logger for this module
logger = logging.getLogger(__name__)

# Dictionary of vector store IDs to their configurations
VECTOR_STORES = {
    "documentation": {
        "name": "Documentation",
        "description": "Technical documentation from the Deepgram docs site"
    }
}

# Tool information registry with descriptions
TOOL_DESCRIPTIONS = {
    "search_documentation": {
        "name": "search_documentation",
        "description": "Search technical documentation from the Deepgram docs site",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-50)"
                }
            },
            "required": ["query"]
        }
    },
}

@register_tool("search_documentation")
async def search_documentation(arguments: Dict[str, Any]) -> Union[VectorSearchResponse, ToolError]:
    """Search technical documentation and API references"""

    # If called with a dictionary of arguments (from a tool call)
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)
    
    if not query:
        return ToolError(error="No search query provided")

    target_url = "https://api.openai.com/v1/vector_stores/vs_67ff646e0558819189933696b5b165b1/search"

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Prepare the request payload
    payload = {
        "query": query,
        "max_num_results": limit  # Use max_num_results instead of limit
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )

            if response.status_code == 200:
                response_json = response.json()
                
                # Create a compatible VectorSearchResponse
                search_response = VectorSearchResponse()
            
                data_items = []
                for item in response_json.get("data", []):
                    content_items = []
                    
                    # Process content array
                    for content in item.get("content", []):
                        content_items.append(ContentItem(
                            type=content.get("type", "text"),
                            text=content.get("text", "")
                        ))
                    
                    # Create data item
                    data_item = VectorSearchDataItem(
                        file_id=item.get("file_id"),
                        filename=item.get("filename"),
                        score=item.get("score"),
                        attributes=item.get("attributes", {}),
                        content=content_items
                    )
                    data_items.append(data_item)
                
                search_response.data = data_items
                search_response.object = response_json.get("object")
                search_response.search_query = response_json.get("search_query")
                search_response.has_more = response_json.get("has_more")
                search_response.next_page = response_json.get("next_page")

                logger.info(f"Search response items: {len(search_response.data)}")
                
                return search_response
            else:
                # Extract error information from the response
                error_data = response_json.get("error", {})
                
                # If the error is a dictionary, convert it to a string representation
                if isinstance(error_data, dict):
                    # Check for common error message structures
                    if "error" in error_data:
                        error_value = error_data["error"]
                        if isinstance(error_value, dict) and "message" in error_value:
                            error_message = error_value["message"]
                        elif isinstance(error_value, str):
                            error_message = error_value
                        else:
                            error_message = str(error_value)
                    elif "message" in error_data:
                        error_message = error_data["message"]
                    else:
                        # Fallback to string representation of the whole error object
                        error_message = str(error_data)
                else:
                    error_message = str(error_data)
                
                logger.error(f"Vector store API error: {error_message}")
                return ToolError(error=error_message)
    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        return ToolError(error=f"Vector search failed: {str(e)}")
