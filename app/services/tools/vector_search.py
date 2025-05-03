import logging
import httpx
from typing import Dict, Any

from app.config import settings
from app.services.tools.registry import register_tool

# Get a logger for this module
logger = logging.getLogger(__name__)

@register_tool(
    name="search_documentation",
    description="""
Search technical documentation from the Deepgram docs site.

This tool is also called for retrieval-augmented generation (RAG) on chat completion requests. So use it if we need to enrich context further.
    """,
    parameters={
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
    },
    scope="public"
)
async def search_documentation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search technical documentation and API references"""

    # If called with a dictionary of arguments (from a tool call)
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)
    
    if not query:
        return {"error": "No search query provided"}

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
                logger.debug(f"Raw search response: {len(response_json.get('data', []))} items")
                
                # Create a serializable response dictionary
                search_response = {
                    "object": response_json.get("object"),
                    "search_query": response_json.get("search_query"),
                    "has_more": response_json.get("has_more"),
                    "next_page": response_json.get("next_page"),
                    "data": []
                }
            
                # Process and transform the data items
                for item in response_json.get("data", []):
                    content_items = []
                    
                    # Process content array
                    for content in item.get("content", []):
                        content_items.append({
                            "type": content.get("type", "text"),
                            "text": content.get("text", "")
                        })
                    
                    # Create serializable data item
                    data_item = {
                        "file_id": item.get("file_id"),
                        "filename": item.get("filename"),
                        "score": item.get("score"),
                        "attributes": item.get("attributes", {}),
                        "content": content_items,
                        # Add text property for convenience
                        "text": " ".join([c.get("text", "") for c in item.get("content", []) if c.get("type") == "text"])
                    }
                    search_response["data"].append(data_item)

                logger.info(f"Search response items: {len(search_response['data'])}")
                return search_response
            else:
                error_message = "Unknown error"
                try:
                    response_json = response.json()
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
                except Exception as e:
                    error_message = f"Failed to parse error response: {str(e)}"
                
                logger.error(f"Vector store API error: {error_message}")
                return {"error": error_message}
    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        return {"error": f"Vector search failed: {str(e)}"}
