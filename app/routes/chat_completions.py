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
from app.services.tools.vector_search import search_documentation
from app.services.tools.registry import tools

# Get a logger for this module
logger = logging.getLogger(__name__)

OPENAI_CHAT_COMPLETIONS_ENDPOINT = "https://api.openai.com/v1/chat/completions"

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
    context = "I found the following relevant information that might help:\n\n"
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
    
    # Convert all messages to dictionaries for JSON serialization
    serialized_messages = []
    for msg in messages:
        if isinstance(msg, ChatMessage):
            serialized_messages.append(msg.model_dump())
        else:
            serialized_messages.append(msg)
    
    # Insert the system message as a dictionary
    system_message_dict = system_message.model_dump()
    
    if last_user_index is not None:
        # Insert the system message before the last user message
        enriched_messages = serialized_messages[:last_user_index] + [system_message_dict] + serialized_messages[last_user_index:]
        return enriched_messages
    
    # If no user message found, just append the system message
    return serialized_messages + [system_message_dict]


@post("/chat/completions")
async def chat_completion(request: Request, data: Any) -> Response:
    """
    Proxy requests to the chat completion API.
    Before sending to the LLM, performs vector search for retrieval augmented generation.
    Also injects tools and processes tool calls if needed.
    """
    
    # Log the proxy destination
    logger.info(f"Proxying request to: {OPENAI_CHAT_COMPLETIONS_ENDPOINT}")
    
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

        # log the query
        logger.info(f"Query: {query}")

        # Perform vector search of documentation if we have a query
        if query:
            try:
                search_results = await search_documentation({"query": query})

                # Check if we have search results and prepare them for enrichment
                search_items = []
                
                # Handle both data and matches fields for flexibility
                if hasattr(search_results, 'data') and search_results.data:
                    for item in search_results.data:
                        item_dict = {
                            "content": item.text if hasattr(item, 'text') else " ".join([c.text for c in item.content]),
                            "metadata": item.attributes if hasattr(item, 'attributes') else {}
                        }
                        
                        # Add filename to metadata if available
                        if hasattr(item, 'filename') and item.filename:
                            item_dict["metadata"]["title"] = item.filename
                            
                        search_items.append(item_dict)
                elif hasattr(search_results, 'matches') and search_results.matches:
                    for match in search_results.matches:
                        match_dict = {}
                        
                        # Handle content
                        if hasattr(match, 'text') and match.text:
                            match_dict["content"] = match.text
                        elif hasattr(match, 'content') and match.content:
                            if isinstance(match.content, list):
                                match_dict["content"] = " ".join([c.text for c in match.content])
                            else:
                                match_dict["content"] = match.content
                                
                        # Handle metadata
                        if hasattr(match, 'metadata') and match.metadata:
                            match_dict["metadata"] = match.metadata
                        elif hasattr(match, 'attributes') and match.attributes:
                            match_dict["metadata"] = match.attributes
                            
                        search_items.append(match_dict)
                
                # Enrich the messages with RAG results if we have any
                if search_items:
                    json_data["messages"] = enrich_messages_with_rag_results(
                        messages, 
                        search_items
                    )
                
            except Exception as e:
                logger.warning(f"Error during vector search: {str(e)}")
                # Continue without RAG if search fails

        # For streaming responses
        if getattr(data, 'stream', False) or json_data.get('stream', False):
            logger.info("Streaming response enabled")
            return await handle_streaming_response(OPENAI_CHAT_COMPLETIONS_ENDPOINT, headers, json_data)
        
        # For non-streaming responses, we need to handle tool calls
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_ENDPOINT,
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
                    
                    # Process all tool calls - let errors propagate
                    tool_results = {}
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.get("id")
                        # Process tool call and let exceptions propagate
                        result = await process_tool_call(tool_call)
                        tool_results[tool_call_id] = result
                    
                    # Create a new request with tool results
                    new_messages = json_data.get("messages", []).copy()
                    new_messages.append(choice["message"])
                    
                    # Add tool results
                    for tool_call_id, result in tool_results.items():

                        # Serialize the result
                        result_json = json.dumps(result)
                        
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
                        OPENAI_CHAT_COMPLETIONS_ENDPOINT,
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
        
        # Check if this is a vector store error and provide more specific information
        error_msg = str(e)
        if "vector" in error_msg.lower() or "rag" in error_msg.lower():
            detail = f"RAG search failed: {error_msg}"
        else:
            detail = str(e)
            
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=detail,
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


async def process_tool_call(tool_call: Dict[str, Any]) -> Any:
    """
    Process a tool call by extracting the function name and arguments and dispatching
    to the appropriate tool handler.
    
    Args:
        tool_call: The tool call object from the OpenAI API
        
    Returns:
        The result of the tool call
        
    Raises:
        HTTPException: If the tool is not found or there's an error processing the call
    """
    try:
        # Extract function details
        if not tool_call.get("function"):
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail="Tool call missing function details"
            )
            
        function = tool_call["function"]
        function_name = function.get("name")
        
        if not function_name:
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail="Tool call missing function name"
            )
            
        # Check if the tool exists
        if function_name not in tools:
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=f"Tool '{function_name}' not found"
            )
            
        # Parse arguments
        arguments_str = function.get("arguments", "{}")
        
        # Ensure arguments is a string (not a dict)
        if isinstance(arguments_str, dict):
            arguments = arguments_str
        else:
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                # If it's not valid JSON, use an empty dict
                logger.warning(f"Invalid JSON in tool arguments: {arguments_str}")
                arguments = {}
        
        # Call the tool function
        logger.info(f"Calling tool: {function_name} with arguments: {arguments}")
        result = await tools[function_name](arguments)
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log and wrap other exceptions
        logger.error(f"Error processing tool call: {str(e)}")
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=f"Error processing tool call: {str(e)}"
        )


# Create the router with the handler function
chat_completions_router = Router(
    path="/v1",
    route_handlers=[chat_completion],
    tags=["Chat Completions API"],
) 