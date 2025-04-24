import logging
from typing import Any, Dict, Optional

import httpx
from litestar import Router, WebSocket, websocket
from litestar.exceptions import HTTPException

from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for Deepgram's agent API.
    Proxies to wss://agent.deepgram.com/v1/agent
    """
    await socket.accept()
    
    # Create a connection to the Deepgram WebSocket
    deepgram_ws_url = "wss://agent.deepgram.com/v1/agent"
    
    # Log the proxy destination
    logger.info(f"Proxying WebSocket connection to: {deepgram_ws_url}")
    
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Connect to Deepgram WebSocket
            async with client.websocket(deepgram_ws_url, headers=headers) as deepgram_ws:
                # Log successful connection
                logger.info(f"Connected to Deepgram WebSocket at {deepgram_ws_url}")
                
                # Create tasks for bidirectional communication
                # Forward messages from client to Deepgram
                client_task = socket.receive_text()
                # Forward messages from Deepgram to client
                deepgram_task = deepgram_ws.receive_text()
                
                while True:
                    # Wait for client to send a message
                    client_message = await client_task
                    logger.debug(f"Received message from client: {client_message[:100]}...")
                    
                    # Send to Deepgram
                    await deepgram_ws.send_text(client_message)
                    
                    # Wait for Deepgram response
                    deepgram_message = await deepgram_task
                    logger.debug(f"Received message from Deepgram: {deepgram_message[:100]}...")
                    
                    # Send to client
                    await socket.send_text(deepgram_message)
                    
                    # Reset tasks for next iteration
                    client_task = socket.receive_text()
                    deepgram_task = deepgram_ws.receive_text()
    
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        await socket.send_text(f"Error: {str(e)}")
        await socket.close()


deepgram_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Deepgram Agent Proxy"],
) 