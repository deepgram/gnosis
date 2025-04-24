from typing import Any, Dict, List, Optional, Union

import httpx
from litestar import Router, Request, Response, WebSocket, get, post
from litestar.datastructures import State
from litestar.exceptions import HTTPException
from litestar.response import Stream
from litestar.status_codes import HTTP_502_BAD_GATEWAY

from app.config import settings
from app.models.openai import ChatCompletionRequest, ChatCompletionResponse
from app.interceptors.tool_handler import process_tool_calls


async def proxy_chat_completion(request: Request, data: ChatCompletionRequest) -> Union[ChatCompletionResponse, Stream]:
    """
    Proxy requests to OpenAI's chat completion API with tool call interception.
    """
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Inject function/tool definitions if not already present
    if not data.tools and not data.functions:
        # Add our custom tools
        data = await inject_custom_tools(data)
    
    # Handle streaming responses differently
    if data.stream:
        return Stream(
            stream_chat_completion_response(request, data, headers),
            media_type="text/event-stream"
        )
    
    # For non-streaming responses
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.OPENAI_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=data.model_dump(exclude_none=True),
                timeout=60.0,
            )
            
            response_data = response.json()
            
            # Process any tool calls before returning
            if "choices" in response_data and response_data["choices"]:
                choice = response_data["choices"][0]
                if "message" in choice and "tool_calls" in choice["message"]:
                    response_data = await process_tool_calls(response_data)
            
            return ChatCompletionResponse(**response_data)
        
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text,
            )
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=str(e),
            )


async def stream_chat_completion_response(request: Request, data: ChatCompletionRequest, headers: Dict[str, str]):
    """
    Stream response from OpenAI's chat completion API.
    """
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.OPENAI_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=data.model_dump(exclude_none=True),
                timeout=60.0,
            ) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        # Process streaming tool calls if needed
                        processed_chunk = await process_streaming_tool_calls(chunk)
                        yield processed_chunk
        
        except httpx.HTTPStatusError as e:
            yield f"error: {e.response.text}"
        except Exception as e:
            yield f"error: {str(e)}"


async def inject_custom_tools(data: ChatCompletionRequest) -> ChatCompletionRequest:
    """
    Inject our custom tools into the request.
    """
    # Add our built-in tools
    # These would come from a tools registry in a real implementation
    data.tools = [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base for relevant information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        # Add other tools as needed
    ]
    
    return data


async def process_streaming_tool_calls(chunk: str) -> str:
    """
    Process streaming tool calls from OpenAI.
    """
    # In a real implementation, this would inspect streaming chunks
    # and intercept tool calls as needed
    return chunk


openai_router = Router(
    path="/v1",
    route_handlers=[
        post("/chat/completions", handler=proxy_chat_completion),
    ],
    tags=["OpenAI Proxy"],
) 