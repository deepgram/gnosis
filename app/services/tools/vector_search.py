import structlog
import httpx
from typing import Dict, Any

from app.config import settings
from app.services.tools.registry import register_tool

# Get a logger for this module
log = structlog.get_logger()


@register_tool(
    name="search_documentation",
    description="""
Search technical documentation from the Deepgram docs site.

Only search if the context is not enough to answer the question.
    """,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (1-2)",
            },
        },
        "required": ["query"],
    },
    scope="public",
)
async def search_documentation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search technical documentation and API references using OpenAI's vector store API.

    Args:
        arguments: Dictionary containing 'query' and optional 'limit'

    Returns:
        Dict containing the search results in the OpenAI vector store API format

    Raises:
        ValueError if the query is empty
        HTTPError for API issues
    """
    # Extract arguments
    query = arguments.get("query", "")
    limit = arguments.get("limit", 2)

    if not query:
        # Return an empty response rather than raising an error
        return {
            "object": "vector_store.search_results.page",
            "search_query": query,
            "data": [],
            "has_more": False,
            "next_page": None,
        }

    target_url = "https://api.openai.com/v1/vector_stores/vs_67ff646e0558819189933696b5b165b1/search"

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Prepare the request payload
    payload = {
        "query": query,
        "max_num_results": limit,
        "ranking_options": {
            "score_threshold": 0.9,
        },
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
                # Parse the response JSON directly
                response_json = response.json()
                log.debug(
                    f"Raw search response: {len(response_json.get('data', []))} items"
                )

                # Return the response directly - it's already in the correct format
                log.info(
                    f"Search response contains {len(response_json.get('data', []))} items"
                )
                return response_json
            else:
                # Handle API errors
                error_message = "Unknown error"
                try:
                    response_json = response.json()
                    # Extract error information from the response
                    error_data = response_json.get("error", {})

                    if isinstance(error_data, dict) and "message" in error_data:
                        error_message = error_data["message"]
                    else:
                        error_message = str(error_data)
                except Exception as e:
                    error_message = f"Failed to parse error response: {str(e)}"

                log.error(f"Vector store API error: {error_message}")
                # Return an empty response with error in the object field
                return {
                    "object": f"error: {error_message}",
                    "search_query": query,
                    "data": [],
                    "has_more": False,
                    "next_page": None,
                }
    except Exception as e:
        log.error(f"Vector search error: {str(e)}")
        # Return an empty response with error in the object field
        return {
            "object": f"error: {str(e)}",
            "search_query": query,
            "data": [],
            "has_more": False,
            "next_page": None,
        }


def format_search_result(search_result: Dict[str, Any]) -> str:
    """
    Format the search result into a markdown string.
    """
    return f"""
## {search_result.get("filename", "Documentation")}

{search_result.get("content", "")}

**Source**: {search_result.get("filename", "Documentation")}
**Relevance**: {search_result.get("score", 0.0):.2f}
"""
