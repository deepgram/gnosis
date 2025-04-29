import json
import logging
from typing import Any, Dict, List, Union

import httpx
from litestar import Router, Request, post
from litestar.exceptions import HTTPException
from litestar.response import Stream, Response
from litestar.status_codes import HTTP_502_BAD_GATEWAY
from pydantic import BaseModel

from app.config import settings
from app.models.chat import ChatMessage, ChatCompletionRequest, ToolResultMessage
from app.models.tools import ToolResponse, VectorSearchResponse
from app.services.tools.vector_search import format_vector_search_results
from app.services.tools.registry import get_all_tool_definitions, tools
from app.services.openai import get_client, perform_vector_search

# Get a logger for this module
logger = logging.getLogger(__name__)

# Get OpenAI client
client = get_client()


# Custom JSON encoder for serializing Pydantic models
class PydanticJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models."""
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)


def extract_query_from_messages(messages: List[Union[ChatMessage, Dict[str, Any]]]) -> str:
    """
    Extract the query from the last user message in the messages array.
    
    Args:
        messages: List of chat messages
        
    Returns:
        The content of the last user message
    """
    if not messages:
        return ""
    
    # Iterate through messages in reverse to find the last user message
    for message in reversed(messages):
        # Convert dict to ChatMessage if needed
        if isinstance(message, dict):
            message = ChatMessage(**message)
            
        if message.role == "user":
            content = message.content or ""
            # Handle both string and list content formats
            if isinstance(content, list):
                # Join text parts of the content
                return " ".join([
                    part.text or ""
                    for part in content
                    if part.type == "text"
                ])
            return content
    
    return ""


def enrich_messages_with_rag_results(
    messages: List[Union[ChatMessage, Dict[str, Any]]], 
    search_results: List[Dict[str, Any]]
) -> List[Union[ChatMessage, Dict[str, Any]]]:
    """
    Add a system message with RAG results before the user's query.
    
    Args:
        messages: The original message list
        search_results: The results from the vector search
        
    Returns:
        The enriched message list
    """
    if not search_results:
        return messages
    
    # Format the search results as context
    context = "I found the following relevant information that might help with your query:\n\n"
    for i, result in enumerate(search_results):
        context += f"--- Result {i+1} ---\n"
        if result.get("metadata", {}).get("title"):
            context += f"Title: {result['metadata']['title']}\n"
        context += f"{result['content']}\n\n"
    
    # Create a new system message with the context
    system_message = ChatMessage(
        role="system",
        content=context
    )
    
    # Find the position to insert the system message
    # We want to insert it just before the last user message
    last_user_index = None
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = msg.get("role") if isinstance(msg, dict) else msg.role
        if role == "user":
            last_user_index = i
            break
    
    if last_user_index is not None:
        # Insert the system message before the last user message
        enriched_messages = messages[:last_user_index] + [system_message] + messages[last_user_index:]
        return enriched_messages
    
    # If no user message found, just append the system message
    return messages + [system_message]


async def process_tool_call(tool_call: Dict[str, Any]) -> ToolResponse:
    """
    Process a tool call from the LLM.
    
    Args:
        tool_call: The tool call data from the LLM
        
    Returns:
        The result of the tool call
        
    Raises:
        Exception: If the tool call fails
    """
    tool_name = tool_call.get("function", {}).get("name")
    arguments_str = tool_call.get("function", {}).get("arguments", "{}")
    
    # Parse arguments
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse arguments: {arguments_str}")
        raise ValueError(f"Invalid arguments format: {arguments_str}")
    
    # Check if the tool exists
    if tool_name not in tools:
        logger.error(f"Tool not found: {tool_name}")
        raise ValueError(f"Tool not found: {tool_name}")
    
    # Call the tool handler
    logger.info(f"Calling tool: {tool_name}")
    result = await tools[tool_name](arguments)
    logger.info(f"Tool {tool_name} completed successfully")
    return result


@post("/chat/completions")
async def chat_completion(request: Request, data: Any) -> Response:
    """
    Proxy requests to the chat completion API.
    Before sending to the LLM, performs vector search for retrieval augmented generation.
    Also injects tools and processes tool calls if needed.
    """
    # Target URL for the proxy request
    target_url = "https://api.openai.com/v1/chat/completions"
    
    # Log the proxy destination
    logger.info(f"Proxying request to: {target_url}")
    
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Convert data to Pydantic model if possible
    if not isinstance(data, ChatCompletionRequest) and hasattr(data, "__dict__"):
        try:
            data = ChatCompletionRequest(**data.model_dump(exclude_none=True) 
                                        if hasattr(data, 'model_dump') 
                                        else data.__dict__)
        except Exception as e:
            logger.debug(f"Failed to convert data to ChatCompletionRequest: {e}")
    
    # Convert data to JSON-serializable dict
    json_data = data.model_dump(exclude_none=True) if hasattr(data, 'model_dump') else data
    
    try:
        # Extract the query from the messages
        messages = json_data.get("messages", [])
        query = extract_query_from_messages(messages)
        
        # Check if there are tools in the request
        has_tools = "tools" in json_data and json_data["tools"]
        tool_choice = json_data.get("tool_choice", None)
        
        # If no tools specified, inject our tools
        if not has_tools:
            # Add our tools to the request
            json_data["tools"] = get_all_tool_definitions()
            # Only use tools when required
            json_data["tool_choice"] = "auto"
            logger.info("Injected tool definitions into request")
        
        # Perform RAG search if a query was found and there's no direct tool call being made
        if query and tool_choice != "required":
            try:
                # Perform vector search using the query
                logger.info(f"Performing RAG search with query: {query}")
                search_results = await perform_vector_search(query)
                
                if search_results:
                    # Enrich the messages with RAG results
                    json_data["messages"] = enrich_messages_with_rag_results(messages, search_results)
                    logger.info("Successfully enriched request with RAG results")
            except Exception as e:
                # If RAG search fails, return a 500 error instead of continuing without context
                logger.error(f"Vector search failed: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_502_BAD_GATEWAY,
                    detail=f"RAG search failed: {str(e)}"
                )
        
        # For streaming responses
        if getattr(data, 'stream', False) or json_data.get('stream', False):
            logger.info("Streaming response enabled")
            return await handle_streaming_response(target_url, headers, json_data)
        
        # For non-streaming responses, we need to handle tool calls
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                headers=headers,
                json=json_data,
                timeout=60.0,
            )
            
            # Log the status code
            logger.info(f"Received response with status code: {response.status_code}")
            
            # Parse the response
            response_data = response.json()
            
            # Check if there's a tool call in the response
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                
                if "message" in choice and "tool_calls" in choice["message"]:
                    tool_calls = choice["message"]["tool_calls"]
                    
                    # Process all tool calls
                    tool_results = {}
                    try:
                        for tool_call in tool_calls:
                            tool_call_id = tool_call.get("id")
                            result = await process_tool_call(tool_call)
                            tool_results[tool_call_id] = result
                    except Exception as e:
                        # If tool call processing fails, return a 500 error
                        logger.error(f"Tool call processing failed: {str(e)}")
                        raise HTTPException(
                            status_code=HTTP_502_BAD_GATEWAY,
                            detail=f"Tool call failed: {str(e)}"
                        )
                    
                    # Create a new request with tool results
                    new_messages = json_data.get("messages", []).copy()
                    new_messages.append(choice["message"])
                    
                    # Add tool results
                    for tool_call_id, result in tool_results.items():
                        # Serialize the result using our custom encoder if needed
                        try:
                            # Make sure we serialize any Pydantic models in the result
                            if isinstance(result, BaseModel):
                                result_json = json.dumps(result.model_dump(), cls=PydanticJSONEncoder)
                            else:
                                result_json = json.dumps(result, cls=PydanticJSONEncoder)
                        except TypeError:
                            # Fallback to string representation if serialization fails
                            result_json = json.dumps(str(result))
                        
                        # Create tool result message
                        tool_message = ToolResultMessage(
                            role="tool",
                            tool_call_id=tool_call_id,
                            content=result_json
                        )
                        
                        # Add tool result message as dict for serialization
                        new_messages.append(tool_message.model_dump())
                    
                    # Create new request to send back to LLM
                    new_json_data = json_data.copy()
                    new_json_data["messages"] = new_messages
                    
                    # Send the follow-up request
                    logger.info("Sending follow-up request with tool results")
                    follow_up_response = await client.post(
                        target_url,
                        headers=headers,
                        json=new_json_data,
                        timeout=60.0,
                    )
                    
                    # Return the final response
                    return Response(
                        content=follow_up_response.content,
                        status_code=follow_up_response.status_code,
                        headers={"Content-Type": follow_up_response.headers.get("Content-Type", "application/json")},
                    )
            
            # Return the original response if no tool calls
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Content-Type": response.headers.get("Content-Type", "application/json")},
            )
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text,
        )
    except TypeError as e:
        # This is likely a JSON serialization error
        logger.error(f"TypeError (likely JSON serialization error): {str(e)}")
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=f"JSON serialization error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}")
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


async def handle_streaming_response(target_url, headers, json_data):
    """
    Handle streaming responses with tool call support.
    """
    # Streaming with tool calls is more complex and would need a specialized implementation
    # For this example, we'll just support basic streaming without tool calls
    return Stream(
        stream_chat_completion_response(target_url, headers, json_data),
        media_type="text/event-stream"
    )


async def stream_chat_completion_response(target_url, headers, json_data):
    """
    Stream response from chat completion API.
    """
    try:
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "POST",
                target_url,
                headers=headers,
                json=json_data,
                timeout=60.0,
            ) as response:
                logger.info(f"Streaming response with status code: {response.status_code}")
                
                async for chunk in response.aiter_lines():
                    if chunk:
                        yield chunk
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error (streaming): {e.response.status_code} - {e.response.text}")
        yield f"data: {{\"error\":{{\"message\":\"{e.response.text}\"}}}}\n\n"
    except Exception as e:
        logger.error(f"Error streaming: {str(e)}")
        yield f"data: {{\"error\":{{\"message\":\"{str(e)}\"}}}}\n\n"


# Create the router with the handler function
chat_completions_router = Router(
    path="/v1",
    route_handlers=[chat_completion],
    tags=["Chat Completions API"],
) 