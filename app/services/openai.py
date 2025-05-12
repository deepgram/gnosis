"""
OpenAI service for making API requests.

This service provides a clean interface for making requests to OpenAI APIs.
"""

import json
from typing import (
    Dict,
    Any,
    AsyncGenerator,
    Optional,
    Union,
    TypeVar,
)

import httpx
import structlog
from pydantic import BaseModel

from app.config import settings
from app.models.chat import ChatCompletionRequest
from app.models.vector_store import VectorStoreSearchRequest
from litestar.response import Response

# Get a logger for this module
# log = structlog.get_logger()

# OpenAI API endpoints
OPENAI_BASE_URL = "https://api.openai.com"

T = TypeVar("T", bound=BaseModel)


class OpenAIService:
    """Service for interacting with OpenAI APIs."""

    @staticmethod
    def _get_headers() -> Dict[str, str]:
        """
        Get the required headers for OpenAI API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

    @staticmethod
    async def make_request(
        endpoint: str,
        method: str = "POST",
        data: Optional[BaseModel] = None,
        timeout: float = 60.0,
        stream: bool = False,
    ) -> Union[Response, AsyncGenerator[Dict[str, Any], None]]:
        """
        Make a request to OpenAI API.

        Args:
            endpoint: API endpoint path (will be appended to base URL)
            method: HTTP method (GET, POST, etc.)
            data: Pydantic model request data
            timeout: Request timeout in seconds
            stream: Whether to stream the response

        Returns:
            Response object or async generator for streaming
        """
        url = f"{OPENAI_BASE_URL}{endpoint}"
        headers = OpenAIService._get_headers()

        if data is None:
            raise ValueError("Data is required")

        # Convert Pydantic model to dict if needed
        request_data = data.model_dump()

        async with httpx.AsyncClient() as client:
            if stream:
                return OpenAIService._stream_response(
                    client=client,
                    url=url,
                    method=method,
                    headers=headers,
                    data=request_data,
                    timeout=timeout,
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=request_data,
                    timeout=timeout,
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )

    @staticmethod
    async def _stream_response(
        client: httpx.AsyncClient,
        url: str,
        method: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]],
        timeout: float,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from OpenAI API.

        Args:
            client: HTTPX client
            url: Request URL
            method: HTTP method
            headers: Request headers
            data: Request data
            timeout: Request timeout

        Yields:
            Parsed SSE messages
        """
        async with client.stream(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=timeout,
        ) as response:
            if response.status_code >= 400:
                response.raise_for_status()

            # Process server-sent events
            async for line in response.aiter_lines():
                if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                    try:
                        chunk = json.loads(line[6:])
                        yield chunk
                    except json.JSONDecodeError as e:
                        # Continue to next chunk instead of yielding None
                        continue

    @staticmethod
    async def create_chat_completion(
        data: ChatCompletionRequest,
        timeout: float = 60.0,
        stream: bool = False,
    ) -> Union[Response, AsyncGenerator[Dict[str, Any], None]]:
        """
        Create a chat completion with OpenAI.

        Args:
            request_data: The request data to send (Pydantic model)
            timeout: Request timeout in seconds
            stream: Whether to stream the response

        Returns:
            Response object
        """
        endpoint = "/v1/chat/completions"
        return await OpenAIService.make_request(
            endpoint=endpoint,
            data=data,
            timeout=timeout,
            stream=stream,
        )

    @staticmethod
    async def search_vector_store(
        store_id: str,
        data: VectorStoreSearchRequest,
        timeout: float = 60.0,
    ) -> Response:
        """
        Search OpenAI vector store.

        Args:
            store_id: The ID of the vector store to search
            query: The search query parameters (Pydantic model)
            timeout: Request timeout in seconds

        Returns:
            Response object
        """
        endpoint = f"/v1/vector_stores/{store_id}/search"
        result = await OpenAIService.make_request(
            endpoint=endpoint,
            data=data,
            timeout=timeout,
            stream=False,
        )
        if isinstance(result, AsyncGenerator):
            # Handle streaming response
            # In practice this shouldn't happen when stream=False
            raise ValueError("Unexpected streaming response")
        return result
