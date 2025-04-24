import json
import logging
from typing import Any, Dict, Union

import httpx
from litestar import Router, Request, post
from litestar.exceptions import HTTPException
from litestar.response import Stream, Response
from litestar.status_codes import HTTP_502_BAD_GATEWAY

from app.config import settings
from app.models.openai import ChatCompletionRequest

# Get a logger for this module
logger = logging.getLogger(__name__)


@post("/chat/completions")
async def proxy_chat_completion(request: Request, data: ChatCompletionRequest) -> Response:
    """
    Proxy requests to OpenAI's chat completion API.
    Proxies to https://api.openai.com/v1/chat/completions
    """
    # Target URL for the proxy request
    target_url = "https://api.openai.com/v1/chat/completions"
    
    # Log the proxy destination
    logger.info(f"Proxying request to: {target_url}")
    
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # For non-streaming responses, we just proxy directly
    async with httpx.AsyncClient() as client:
        try:
            # For streaming responses
            if data.stream:
                logger.info("Streaming response enabled")
                return await handle_streaming_response(client, target_url, headers, data)
            
            # For regular responses
            response = await client.post(
                target_url,
                headers=headers,
                json=data.model_dump(exclude_none=True),
                timeout=60.0,
            )
            
            # Log the status code
            logger.info(f"Received response from OpenAI with status code: {response.status_code}")
            
            # Return the response directly
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Content-Type": response.headers.get("Content-Type", "application/json")},
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from OpenAI: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text,
            )
        except Exception as e:
            logger.error(f"Error proxying to OpenAI: {str(e)}")
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail=str(e),
            )


async def handle_streaming_response(client, target_url, headers, data):
    """
    Handle streaming responses from OpenAI.
    """
    return Stream(
        stream_chat_completion_response(client, target_url, headers, data),
        media_type="text/event-stream"
    )


async def stream_chat_completion_response(client, target_url, headers, data):
    """
    Stream response from OpenAI's chat completion API.
    """
    try:
        async with client.stream(
            "POST",
            target_url,
            headers=headers,
            json=data.model_dump(exclude_none=True),
            timeout=60.0,
        ) as response:
            logger.info(f"Streaming response from OpenAI with status code: {response.status_code}")
            
            async for chunk in response.aiter_lines():
                if chunk:
                    yield chunk
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from OpenAI (streaming): {e.response.status_code} - {e.response.text}")
        yield f"data: {{\"error\":{{\"message\":\"{e.response.text}\"}}}}\n\n"
    except Exception as e:
        logger.error(f"Error streaming from OpenAI: {str(e)}")
        yield f"data: {{\"error\":{{\"message\":\"{str(e)}\"}}}}\n\n"


# Create the router with the handler function
openai_router = Router(
    path="/v1",
    route_handlers=[proxy_chat_completion],
    tags=["OpenAI Chat Completions Proxy"],
) 