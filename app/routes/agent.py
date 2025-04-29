import logging
import json
import time
import asyncio
from typing import Dict, Any

from litestar import Router, WebSocket, websocket

from app.services.deepgram import handle_agent_session

# Get a logger for this module
logger = logging.getLogger(__name__)


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for voice agent API.
    Proxies to Deepgram's agent API.
    """
    await socket.accept()
    
    # Log the proxy destination
    logger.info("Proxying WebSocket connection to voice agent")
    
    # Generate a unique session ID
    session_id = f"session-{int(time.time())}"
    
    # Define message handlers for the socket
    async def receive_from_client():
        return await socket.receive()
    
    async def send_to_client(message):
        if message["type"] == "text":
            await socket.send_text(message["content"])
        elif message["type"] == "binary":
            await socket.send_bytes(message["content"])
    
    try:
        # Handle the agent session
        await handle_agent_session(
            client_socket=socket,
            session_id=session_id,
            on_receive=receive_from_client,
            on_send=send_to_client
        )
    except Exception as e:
        logger.error(f"[{session_id}] Error in agent websocket: {str(e)}")
        error_message = json.dumps({"type": "Error", "message": str(e)})
        await socket.send_text(error_message)
    finally:
        # Ensure client socket is closed
        try:
            await socket.close()
            logger.debug(f"[{session_id}] Closed client socket")
        except Exception as e:
            logger.error(f"[{session_id}] Error closing client socket: {e}")


# Create the router with the handler function
agent_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Voice Agent API"],
) 