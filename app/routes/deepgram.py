import logging
import json
import asyncio
import time
from typing import Any, Dict, Optional, Literal

from litestar import Router, WebSocket, websocket
import websockets

from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)

# Enable detailed debug logging
DEBUG = True

def log_message(direction: Literal["incoming", "outgoing"], source: str, message: str) -> None:
    """
    Log a message with detailed formatting for easier debugging.
    
    Args:
        direction: Whether the message is incoming or outgoing
        source: Source of the message (client or deepgram)
        message: The actual message content
    """
    if not DEBUG:
        return
        
    # Truncate very long messages in logs
    message_preview = message[:200] + "..." if len(message) > 200 else message
    
    try:
        # Try to parse and pretty-print JSON for better debugging
        data = json.loads(message)
        msg_type = data.get("type", "unknown")
        
        if msg_type == "AudioMessage":
            # For audio messages just log the type and length to avoid spamming logs
            audio_data_len = len(data.get("audio", {}).get("data", ""))
            logger.debug(f"{direction.upper()} {source} | Type: {msg_type} | Audio bytes: {audio_data_len}")
        else:
            # Pretty print other message types
            logger.debug(f"{direction.upper()} {source} | Type: {msg_type} | Content: {json.dumps(data, indent=2)}")
            
    except json.JSONDecodeError:
        # Not JSON or invalid JSON
        logger.debug(f"{direction.upper()} {source} | Raw message: {message_preview}")


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for Deepgram's agent API.
    Proxies to wss://api.deepgram.com/v1/agent
    """
    await socket.accept()
    
    # Log the proxy destination
    logger.info("Proxying WebSocket connection to Deepgram Agent API")
    
    # Track connection details for debugging
    session_start = time.time()
    messages_from_client = 0
    messages_to_client = 0
    deepgram_socket = None
    session_id = f"session-{int(session_start)}"
    
    # Main proxy logic
    try:
        # Connect to Deepgram WebSocket
        deepgram_url = "wss://api.deepgram.com/v1/agent"
        logger.info(f"[{session_id}] Connecting to Deepgram at {deepgram_url}")
        
        # Create connection to Deepgram
        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
        
        try:
            deepgram_socket = await asyncio.wait_for(
                websockets.connect(deepgram_url, extra_headers=headers),
                timeout=10.0  # Add reasonable timeout for connection
            )
            logger.info(f"[{session_id}] Connected to Deepgram WebSocket")
        except asyncio.TimeoutError:
            logger.error(f"[{session_id}] Timeout connecting to Deepgram")
            await socket.send_text(json.dumps({
                "type": "Error",
                "message": "Timeout connecting to Deepgram service"
            }))
            return
        except Exception as e:
            logger.error(f"[{session_id}] Failed to connect to Deepgram: {str(e)}")
            await socket.send_text(json.dumps({
                "type": "Error",
                "message": f"Failed to connect to Deepgram: {str(e)}"
            }))
            return
        
        # Forward client messages to Deepgram
        async def forward_client_to_deepgram():
            nonlocal messages_from_client
            try:
                while True:
                    # Get message from client
                    message = await socket.receive_text()
                    messages_from_client += 1
                    
                    # Log the message
                    log_message("outgoing", "client → deepgram", message)
                    
                    # Forward to Deepgram
                    await deepgram_socket.send(message)
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"[{session_id}] Client connection closed (code: {e.code}, reason: {e.reason})")
            except Exception as e:
                logger.error(f"[{session_id}] Error forwarding client → Deepgram: {e}")
                
        # Forward Deepgram responses to client
        async def forward_deepgram_to_client():
            nonlocal messages_to_client
            try:
                while True:
                    # Get response from Deepgram
                    message = await deepgram_socket.recv()
                    messages_to_client += 1
                    
                    # Log the message
                    log_message("incoming", "deepgram → client", message)
                    
                    # Forward to client
                    await socket.send_text(message)
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"[{session_id}] Deepgram connection closed (code: {e.code}, reason: {e.reason})")
            except Exception as e:
                logger.error(f"[{session_id}] Error forwarding Deepgram → client: {e}")
                
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
        logger.error(f"[{session_id}] Error in WebSocket proxy: {str(e)}")
        error_message = json.dumps({"type": "Error", "message": str(e)})
        await socket.send_text(error_message)
    
    finally:
        session_duration = time.time() - session_start
        
        # Log session stats
        logger.info(
            f"[{session_id}] Session ended - Duration: {session_duration:.2f}s, "
            f"Messages from client: {messages_from_client}, Messages to client: {messages_to_client}"
        )
        
        # Ensure both sockets are closed
        try:
            if deepgram_socket and not deepgram_socket.closed:
                await deepgram_socket.close()
                logger.debug(f"[{session_id}] Closed Deepgram socket")
        except Exception as e:
            logger.error(f"[{session_id}] Error closing Deepgram socket: {e}")
            
        try:
            await socket.close()
            logger.debug(f"[{session_id}] Closed client socket")
        except Exception as e:
            logger.error(f"[{session_id}] Error closing client socket: {e}")


deepgram_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Deepgram Agent Proxy"],
) 