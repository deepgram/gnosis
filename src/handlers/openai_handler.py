from typing import Dict, Any
from litestar import Router, post
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.response import Response
from src.services.openai_service import OpenAIService

@post("/v1/chat/completions")
async def handle_openai_proxy(data: Dict[str, Any]) -> Response:
    """Handle HTTP requests to OpenAI's chat completions endpoint"""
    try:
        response_data, status = await OpenAIService.forward_chat_completion(data)
        return Response(content=response_data, status_code=status)
    except Exception as e:
        return Response(
            content={'error': str(e)},
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )

# Create router for organization
openai_router = Router(path="/v1", route_handlers=[handle_openai_proxy]) 