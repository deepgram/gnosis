import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from openai import OpenAI
from app.config import settings
from app.services.tools.registry import register_tool

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Dictionary of vector store IDs to their configurations
VECTOR_STORES = {
    "documentation": {
        "name": "Documentation",
        "description": "Technical documentation and API references"
    },
    "knowledge_base": {
        "name": "Knowledge Base",
        "description": "General knowledge articles and FAQs"
    },
    "code_examples": {
        "name": "Code Examples",
        "description": "Code snippets and programming examples"
    }
}

# Tool information registry with descriptions
TOOL_DESCRIPTIONS = {
    "search_documentation": {
        "name": "search_documentation",
        "description": "Search technical documentation and API references",
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
    "search_knowledge_base": {
        "name": "search_knowledge_base",
        "description": "Search knowledge base articles and FAQs",
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
    "search_code_examples": {
        "name": "search_code_examples",
        "description": "Search code snippets and programming examples",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (e.g., python, javascript)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    }
}

async def vector_store_search(
    query: str,
    vector_store_id: str,
    limit: int = 5,
    additional_params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Abstract function to search a vector store using embeddings.
    
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
        # Get embedding from OpenAI
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        
        embedding = response.data[0].embedding
        
        # Here you would normally search a vector database (Pinecone, Weaviate, etc.)
        # For now, we'll return mock data based on the vector_store_id
        
        # Mock search results for demonstration
        if vector_store_id == "documentation":
            results = [
                {
                    "content": f"Documentation result for '{query}'",
                    "metadata": {
                        "title": "API Reference",
                        "source": "docs/api/v1.md",
                        "vector_store_id": vector_store_id
                    },
                    "score": 0.92
                },
                {
                    "content": f"Another documentation result for '{query}'",
                    "metadata": {
                        "title": "Getting Started",
                        "source": "docs/getting-started.md",
                        "vector_store_id": vector_store_id
                    },
                    "score": 0.85
                }
            ]
        elif vector_store_id == "knowledge_base":
            results = [
                {
                    "content": f"Knowledge base article about '{query}'",
                    "metadata": {
                        "title": "FAQ",
                        "source": "kb/faq.md",
                        "vector_store_id": vector_store_id
                    },
                    "score": 0.88
                }
            ]
        elif vector_store_id == "code_examples":
            # Use additional params for language filtering if provided
            language = additional_params.get("language") if additional_params else None
            language_str = f" in {language}" if language else ""
            
            results = [
                {
                    "content": f"Code example for '{query}'{language_str}",
                    "metadata": {
                        "title": "Code Snippet",
                        "language": language or "python",
                        "source": "examples/snippets.md",
                        "vector_store_id": vector_store_id
                    },
                    "score": 0.91
                }
            ]
        else:
            # Default empty results
            results = []
            
        # Limit results
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error in vector store search: {str(e)}")
        return []

# Tool implementations
@register_tool("search_documentation")
async def search_documentation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search technical documentation and API references"""
    query = arguments.get("query")
    limit = arguments.get("limit", 5)
    
    if not query:
        return {"error": "Query parameter is required"}
    
    results = await vector_store_search(
        query=query,
        vector_store_id="documentation",
        limit=limit
    )
    
    return format_vector_search_results(results)

@register_tool("search_knowledge_base")
async def search_knowledge_base(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search knowledge base articles and FAQs"""
    query = arguments.get("query")
    limit = arguments.get("limit", 5)
    
    if not query:
        return {"error": "Query parameter is required"}
    
    results = await vector_store_search(
        query=query,
        vector_store_id="knowledge_base",
        limit=limit
    )
    
    return format_vector_search_results(results)

@register_tool("search_code_examples")
async def search_code_examples(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search code snippets and programming examples"""
    query = arguments.get("query")
    language = arguments.get("language")
    limit = arguments.get("limit", 5)
    
    if not query:
        return {"error": "Query parameter is required"}
    
    additional_params = {"language": language} if language else None
    
    results = await vector_store_search(
        query=query,
        vector_store_id="code_examples",
        limit=limit,
        additional_params=additional_params
    )
    
    return format_vector_search_results(results)

def get_vector_store_id_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Extract the vector store ID from result metadata"""
    return metadata.get("vector_store_id")

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

async def perform_vector_search(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Perform vector search across all vector stores for RAG.
    
    Args:
        query: The search query
        limit: Maximum number of results to return per store
        
    Returns:
        Combined list of search results
    """
    # Search all vector stores concurrently
    tasks = [
        vector_store_search(query, store_id, limit)
        for store_id in VECTOR_STORES.keys()
    ]
    
    # Gather all results
    all_results = await asyncio.gather(*tasks)
    
    # Flatten results and sort by score
    flattened_results = [
        result for sublist in all_results for result in sublist
    ]
    
    # Sort by score (descending)
    sorted_results = sorted(
        flattened_results,
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    
    # Return top results across all stores
    return sorted_results[:limit] 