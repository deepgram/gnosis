from typing import Any, Dict, Optional

import httpx
from litestar import Router, Request, WebSocket, delete, get, post, websocket
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_502_BAD_GATEWAY

from app.config import settings
from app.models.deepgram import AgentRequest


async def proxy_agent_request(request: Request, data: AgentRequest) -> Dict[str, Any]:
    """
    Proxy requests to Deepgram's agent API.
    """
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Inject our custom interceptors if needed
    data = await inject_custom_capabilities(data)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.DEEPGRAM_BASE_URL}/v1/agent",
                headers=headers,
                json=data.model_dump(exclude_none=True),
                timeout=60.0,
            )
            
            return response.json()
        
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


@websocket("/v1/agent/live")
async def agent_websocket(websocket: WebSocket) -> None:
    """
    Handle WebSocket connections for Deepgram's agent API.
    """
    await websocket.accept()
    
    # Create a connection to the Deepgram WebSocket
    deepgram_ws_url = f"{settings.DEEPGRAM_BASE_URL.replace('https://', 'wss://')}/v1/agent/live"
    
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Connect to Deepgram WebSocket
            async with client.websocket(deepgram_ws_url, headers=headers) as deepgram_ws:
                # Create tasks for bidirectional communication
                # Forward messages from client to Deepgram
                client_task = websocket.receive_text()
                # Forward messages from Deepgram to client
                deepgram_task = deepgram_ws.receive_text()
                
                while True:
                    # Wait for either client or Deepgram to send a message
                    client_message = await client_task
                    
                    # Process the client message (intercept if needed)
                    processed_message = await process_client_message(client_message)
                    
                    # Send to Deepgram
                    await deepgram_ws.send_text(processed_message)
                    
                    # Wait for Deepgram response
                    deepgram_message = await deepgram_task
                    
                    # Process the Deepgram message (intercept if needed)
                    processed_response = await process_deepgram_message(deepgram_message)
                    
                    # Send to client
                    await websocket.send_text(processed_response)
                    
                    # Reset tasks for next iteration
                    client_task = websocket.receive_text()
                    deepgram_task = deepgram_ws.receive_text()
    
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        await websocket.close()


async def inject_custom_capabilities(data: AgentRequest) -> AgentRequest:
    """
    Inject custom capabilities into the agent request.
    """
    # Add our custom capabilities
    # In a real implementation, these would come from a registry
    return data


async def process_client_message(message: str) -> str:
    """
    Process messages from the client to Deepgram.
    """
    # Intercept and modify messages if needed
    return message


async def process_deepgram_message(message: str) -> str:
    """
    Process messages from Deepgram to the client.
    """
    # Intercept and modify messages if needed
    return message


deepgram_router = Router(
    path="/v1",
    route_handlers=[
        post("/agent", handler=proxy_agent_request),
        agent_websocket,
    ],
    tags=["Deepgram Proxy"],
) 