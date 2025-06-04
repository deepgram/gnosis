import json
import structlog
from typing import Dict, Any

from app.services.tools.registry import register_tool
from app.services.openai import OpenAIService
from app.models.vector_store import VectorStoreSearchRequest

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
    query = arguments["query"]
    limit = arguments.get("limit", 2)

    # Prepare the request data
    data = VectorStoreSearchRequest(
        query=query,
        max_num_results=limit,
    )

    response = await OpenAIService.search_vector_store(
        store_id="vs_67ff646e0558819189933696b5b165b1",
        data=data,
    )

    # Convert response to Dict[str, Any]
    response_content = response.content
    try:
        return json.loads(response_content)
    except Exception as e:
        log.error(f"Error parsing response content: {e}")
        return {"error": str(e)}


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
