import logging
import json
import asyncio
from typing import Any, Dict, Optional

import httpx
from litestar import Router, WebSocket, websocket
from litestar.exceptions import HTTPException
import websockets

from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for Deepgram's agent API.
    Proxies to wss://api.deepgram.com/v1/agent
    """
    await socket.accept()
    
    # Log the proxy destination
    logger.info("Proxying WebSocket connection to Deepgram Agent API")
    
    deepgram_socket = None
    
    # Main proxy logic
    try:
        # Connect to Deepgram WebSocket
        deepgram_url = "wss://api.deepgram.com/v1/agent"
        logger.info(f"Connecting to Deepgram at {deepgram_url}")
        
        # Create connection to Deepgram
        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
        deepgram_socket = await websockets.connect(deepgram_url, extra_headers=headers)
        logger.info("Connected to Deepgram WebSocket")
        
        # Forward client messages to Deepgram
        async def forward_client_to_deepgram():
            try:
                while True:
                    # Get message from client
                    message = await socket.receive_text()
                    logger.debug(f"Client → Deepgram: {message[:100]}...")
                    
                    # Forward to Deepgram
                    await deepgram_socket.send(message)
            except websockets.exceptions.ConnectionClosed:
                logger.info("Client connection closed")
            except Exception as e:
                logger.error(f"Error forwarding client → Deepgram: {e}")
                
        # Forward Deepgram responses to client
        async def forward_deepgram_to_client():
            try:
                while True:
                    # Get response from Deepgram
                    message = await deepgram_socket.recv()
                    logger.debug(f"Deepgram → Client: {message[:100]}...")
                    
                    # Forward to client
                    await socket.send_text(message)
            except websockets.exceptions.ConnectionClosed:
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error forwarding Deepgram → client: {e}")
                
        # Run both directions concurrently
        forward_task = asyncio.create_task(forward_client_to_deepgram())
        response_task = asyncio.create_task(forward_deepgram_to_client())
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [forward_task, response_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the remaining task
        for task in pending:
            task.cancel()
            
    except Exception as e:
        logger.error(f"Error in WebSocket proxy: {str(e)}")
        error_message = json.dumps({"type": "Error", "message": str(e)})
        await socket.send_text(error_message)
    
    finally:
        # Ensure both sockets are closed
        try:
            if deepgram_socket and not deepgram_socket.closed:
                await deepgram_socket.close()
        except:
            pass
            
        try:
            await socket.close()
        except:
            pass
            
        logger.info("WebSocket connections closed")


deepgram_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Deepgram Agent Proxy"],
) 