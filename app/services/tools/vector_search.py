import logging
from typing import Dict, List, Any, Optional, Union

from app.config import settings
from app.services.tools.registry import register_tool
from app.services.openai import vector_store_search

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
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    },
}

@register_tool("search_documentation")
async def search_documentation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search technical documentation and API references"""
    query = arguments.get("query")
    limit = arguments.get("limit", 5)
    
    if not query:
        return {"error": "Query parameter is required"}
    
    results = await vector_store_search(
        query=query,
        vector_store_id="vs_67ff646e0558819189933696b5b165b1",
        limit=limit
    )
    
    return format_vector_search_results(results)

def format_vector_search_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format vector search results for return to the LLM"""
    formatted_results = []
    
    for result in results:
        formatted_result = {
            "content": result["content"],
            "metadata": {
                key: value for key, value in result.get("metadata", {}).items()
                if key != "vector_store_id"  # Exclude internal metadata
            }
        }
        
        if "score" in result:
            formatted_result["relevance_score"] = result["score"]
            
        formatted_results.append(formatted_result)
    
    return {
        "results": formatted_results,
        "count": len(formatted_results)
    }
