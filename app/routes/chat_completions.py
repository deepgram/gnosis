import json
import logging
import time
from typing import Any, Dict, List, Union

import httpx
from litestar import Router, Request, post
from litestar.exceptions import HTTPException
from litestar.response import Stream, Response
from litestar.status_codes import HTTP_502_BAD_GATEWAY

from app.config import settings
from app.models.chat import ChatMessage, ChatCompletionRequest, ToolResultMessage, GnosisMetadataItem, GnosisMetadata
from app.services.tools.vector_search import search_documentation, format_search_result
from app.services.tools.registry import get_tool_implementation, execute_tool
from app.services.function_calling import FunctionCallingService

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


@post("/chat/completions")
async def chat_completion(request: Request, data: Any) -> Response:
    """
    Proxy requests to the chat completion API.
    Before sending to the LLM, performs vector search for retrieval augmented generation.
    Also injects tools and processes tool calls if needed.
    """
    
    # Initialize metadata collection
    gnosis_operations = []
    start_time_total = time.time()
    
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
                # 📋 RAG PROCESSING START - Explicit log marker for RAG operations
                logger.info("📋 RAG PROCESSING START - Retrieving augmented context for query")
                
                # Track RAG operation start time
                rag_start_time = time.time()
                
                # Get the search results
                search_results = await search_documentation({
                    "query": query,
                    "limit": 2,
                    "ranking_options": {
                        "score_threshold": 0.9  # Only include highly relevant results
                    }
                })
                
                # Calculate RAG operation duration
                rag_duration_ms = (time.time() - rag_start_time) * 1000
                
                # Log RAG details without modifying the search_documentation function
                logger.info(f"📋 RAG results received: {len(search_results.get('data', []))} items found for query: '{query}'")
                
                # Create metadata entry for RAG operation
                rag_metadata = GnosisMetadataItem(
                    operation_type="rag",
                    name="search_documentation",
                    latency_ms=rag_duration_ms,
                    details={
                        "query": query,
                        "result_count": len(search_results.get("data", []))
                    }
                )
                
                # Add to operations list
                gnosis_operations.append(rag_metadata)

                # Process data items from the search results and add as separate system messages
                data_items = search_results.get("data", [])
                
                if data_items:
                    # Get the original messages to work with
                    original_messages = json_data.get("messages", []).copy()
                    
                    # Find the position of the last user message
                    last_user_index = -1
                    for i in range(len(original_messages) - 1, -1, -1):
                        if original_messages[i].get("role") == "user":
                            last_user_index = i
                            break
                    
                    # Insert position is after the last user message
                    insert_pos = last_user_index + 1 if last_user_index != -1 else len(original_messages)
                    enhanced_messages = original_messages[:insert_pos]
                    
                    # Add each search result as a separate system message in order of relevance
                    for item in data_items:
                        # Extract text from content array and convert to markdown
                        content_text = " ".join([
                            c.get("text", "") 
                            for c in item.get("content", []) 
                            if c.get("type") == "text"
                        ])
                        
                        # Format as markdown with metadata
                        markdown_content = format_search_result(item)

                        
                        # Create system message with this content
                        system_message = {
                            "role": "system",
                            "content": markdown_content
                        }
                        
                        # Add to messages
                        enhanced_messages.append(system_message)
                    
                    # Add remaining messages after the last user message
                    if last_user_index != -1 and last_user_index + 1 < len(original_messages):
                        enhanced_messages.extend(original_messages[last_user_index + 1:])
                    
                    # Update messages in the request
                    json_data["messages"] = enhanced_messages
                    logger.info(f"📋 RAG PROCESSING COMPLETE - Added {len(data_items)} context items as system messages")
                else:
                    logger.info("📋 RAG PROCESSING COMPLETE - No relevant results found")

            except Exception as e:
                logger.warning(f"📋 RAG PROCESSING ERROR - {str(e)}")
                # Continue without RAG if search fails
                # Record the failed operation
                gnosis_operations.append(GnosisMetadataItem(
                    operation_type="rag",
                    name="search_documentation",
                    latency_ms=(time.time() - rag_start_time) * 1000 if 'rag_start_time' in locals() else None,
                    details={"error": str(e), "query": query}
                ))

        # Augment the chat completion request with tool calling configuration
        json_data = FunctionCallingService.augment_openai_request(json_data)

        logger.info(f"Augmented request: {json_data}")

        # Augment the chat completion request with additional metadata
        # json_data['messages'].append(ChatMessage(
        #     role="system",
        #     content=context
        # ))
        
        # Debug log the tools being requested
        if "tools" in json_data:
            logger.debug(f"Request contains {len(json_data['tools'])} tools")
            for tool in json_data['tools']:
                if tool.get("type") == "function" and tool.get("function", {}).get("name"):
                    function_name = tool["function"]["name"]
                    is_internal = function_name.startswith(FunctionCallingService.FUNCTION_PREFIX)
                    logger.debug(f"Tool: {function_name} (Internal: {is_internal})")

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
                    logger.debug(f"Received {len(tool_calls)} tool calls from LLM")
                    
                    # Process all tool calls - let errors propagate
                    tool_results = {}
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.get("id")
                        function_name = tool_call.get("function", {}).get("name", "unknown")
                        is_internal = function_name.startswith(FunctionCallingService.FUNCTION_PREFIX)
                        logger.debug(f"Processing tool call: {function_name} (ID: {tool_call_id}, Internal: {is_internal})")
                        
                        # Track tool call execution time
                        tool_start_time = time.time()
                        
                        try:
                            # Process tool call and let exceptions propagate
                            result = await process_tool_call(tool_call)
                            tool_results[tool_call_id] = result
                            
                            # Calculate tool call duration
                            tool_duration_ms = (time.time() - tool_start_time) * 1000
                            
                            # Record tool call metadata
                            original_name = function_name
                            if is_internal:
                                original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX):]
                                
                            tool_metadata = GnosisMetadataItem(
                                operation_type="tool_call",
                                name=original_name,
                                latency_ms=tool_duration_ms,
                                details={
                                    "tool_call_id": tool_call_id,
                                    "is_internal": is_internal,
                                    "arguments": tool_call.get("function", {}).get("arguments", "{}"),
                                    "result_type": type(result).__name__
                                }
                            )
                            
                            # Add to operations list
                            gnosis_operations.append(tool_metadata)
                            
                            logger.debug(f"Completed tool call {tool_call_id} with result type: {type(result).__name__}")
                        except Exception as e:
                            # Track failed tool call
                            gnosis_operations.append(GnosisMetadataItem(
                                operation_type="tool_call",
                                name=original_name if 'original_name' in locals() else function_name,
                                latency_ms=(time.time() - tool_start_time) * 1000,
                                details={
                                    "tool_call_id": tool_call_id,
                                    "is_internal": is_internal,
                                    "error": str(e)
                                }
                            ))
                            # Re-raise the exception
                            raise
                    
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
                    
                    # Calculate total operation duration
                    total_duration_ms = (time.time() - start_time_total) * 1000
                    
                    # Get the response data
                    follow_up_response_data = follow_up_response.json()
                    
                    # Add Gnosis metadata to the response
                    if "usage" in follow_up_response_data:
                        total_tokens = follow_up_response_data["usage"].get("total_tokens", 0)
                    else:
                        total_tokens = None
                    
                    # Create the metadata
                    metadata = GnosisMetadata(
                        operations=gnosis_operations,
                        total_tokens=total_tokens,
                        total_latency_ms=total_duration_ms,
                        summary=f"Processed {len(gnosis_operations)} operations in {total_duration_ms:.2f}ms"
                    )
                    
                    # Add metadata to response data
                    follow_up_response_data["gnosis_metadata"] = metadata.model_dump(exclude_none=True)
                    
                    # Return the final response with metadata
                    return Response(
                        content=json.dumps(follow_up_response_data),
                        status_code=follow_up_response.status_code,
                        headers={"Content-Type": follow_up_response.headers.get("Content-Type", "application/json")},
                    )
            
            # Calculate total operation duration
            total_duration_ms = (time.time() - start_time_total) * 1000
            
            # Add Gnosis metadata to the original response
            if "usage" in response_data:
                total_tokens = response_data["usage"].get("total_tokens", 0)
            else:
                total_tokens = None
                
            # Create the metadata
            metadata = GnosisMetadata(
                operations=gnosis_operations,
                total_tokens=total_tokens,
                total_latency_ms=total_duration_ms,
                summary=f"Processed {len(gnosis_operations)} operations in {total_duration_ms:.2f}ms"
            )
            
            # Add metadata to response data
            response_data["gnosis_metadata"] = metadata.model_dump(exclude_none=True)
            
            # Return the original response with metadata
            return Response(
                content=json.dumps(response_data),
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
    Handle streaming responses from the chat completion API.
    
    For streaming responses, we don't have a way to modify the chunks in-stream
    since they are handled one at a time. So we'll collect all operations in 
    metadata but won't be able to include it in the response.
    """
    # Create a stream response
    return Stream(
        stream_chat_completion_response(target_url, headers, json_data),
        media_type="text/event-stream",
    )


async def stream_chat_completion_response(target_url, headers, json_data):
    """
    Stream response from chat completion API.
    
    Note: For streaming responses, we can't inject the gnosis_metadata field into the
    stream since we return chunks as they arrive. In a future implementation, we could
    consider collecting the chunks and returning a modified final response with the
    metadata at the end.
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
    start_time = time.time()
    
    try:
        # Extract function details
        if not tool_call.get("function"):
            logger.debug("Tool call missing function details")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail="Tool call missing function details"
            )
            
        function = tool_call["function"]
        function_name = function.get("name")
        
        if not function_name:
            logger.debug("Tool call missing function name")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail="Tool call missing function name"
            )
            
        # Check if the function name has the internal prefix and remove it if it does
        is_internal = function_name.startswith(FunctionCallingService.FUNCTION_PREFIX)
        original_name = function_name
        
        if is_internal:
            original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX):]
            logger.debug(f"Internal tool call detected: {function_name}, using registry name: {original_name}")
        else:
            logger.debug(f"External tool call detected: {function_name}")
        
        # Parse arguments
        arguments_str = function.get("arguments", "{}")
        
        # Ensure arguments is a string (not a dict)
        if isinstance(arguments_str, dict):
            arguments = arguments_str
            logger.debug(f"Tool arguments already in dict format: {len(str(arguments))} chars")
        else:
            try:
                arguments = json.loads(arguments_str)
                logger.debug(f"Parsed tool arguments from JSON: {len(arguments_str)} chars")
            except json.JSONDecodeError:
                # If it's not valid JSON, use an empty dict
                logger.warning(f"Invalid JSON in tool arguments: {arguments_str}")
                arguments = {}
            
        # Check if the tool exists
        if not get_tool_implementation(original_name):
            logger.debug(f"Tool '{original_name}' not found in registry")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=f"Tool '{original_name}' not found"
            )
        
        # 🔧 FUNCTION CALL START - Explicit log marker for function calls
        tool_call_id = tool_call.get("id", "unknown")
        logger.info(f"🔧 FUNCTION CALL START - Executing {original_name} with ID {tool_call_id}")
        
        # Call the tool function using execute_tool helper
        execution_start_time = time.time()
        logger.info(f"Calling tool: {original_name} with arguments: {arguments}")
        result = await execute_tool(original_name, arguments)
        execution_duration_ms = (time.time() - execution_start_time) * 1000
        
        # 🔧 FUNCTION CALL COMPLETE - Explicit log marker for function calls
        logger.info(f"🔧 FUNCTION CALL COMPLETE - {original_name} executed in {execution_duration_ms:.2f}ms")
        logger.debug(f"Tool call completed: {original_name}, result type: {type(result).__name__}, duration: {execution_duration_ms:.2f}ms")
        
        return result
        
    except HTTPException as e:
        # Log with the function call marker
        logger.error(f"🔧 FUNCTION CALL ERROR - {str(e)}")
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log with the function call marker
        logger.error(f"🔧 FUNCTION CALL ERROR - Error processing tool call: {str(e)}")
        # Log and wrap other exceptions
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=f"Error processing tool call: {str(e)}"
        )
    finally:
        # Log total processing time
        total_duration_ms = (time.time() - start_time) * 1000
        logger.debug(f"Total tool call processing time: {total_duration_ms:.2f}ms")


# Create the router with the handler function
chat_completions_router = Router(
    path="/v1",
    route_handlers=[chat_completion],
    tags=["Chat Completions API"],
) 