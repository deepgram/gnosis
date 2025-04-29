import logging
import json
import asyncio
import time
import websockets
from typing import Dict, Any, Callable, Literal

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


async def connect_to_agent(session_id: str) -> websockets.WebSocketClientProtocol:
    """
    Connect to Deepgram Agent API.
    
    Args:
        session_id: A unique session identifier for logging
        
    Returns:
        A connected WebSocket client
        
    Raises:
        Exception: If connection fails
    """
    deepgram_url = "wss://agent.deepgram.com/agent"
    logger.info(f"[{session_id}] Connecting to Deepgram at {deepgram_url}")
    
    # Create connection to Deepgram
    headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
    
    try:
        deepgram_socket = await asyncio.wait_for(
            websockets.connect(deepgram_url, additional_headers=headers),
            timeout=10.0  # Add reasonable timeout for connection
        )
        logger.info(f"[{session_id}] Connected to Deepgram WebSocket")
        return deepgram_socket
    except asyncio.TimeoutError:
        logger.error(f"[{session_id}] Timeout connecting to Deepgram")
        raise TimeoutError("Timeout connecting to Deepgram service")
    except Exception as e:
        logger.error(f"[{session_id}] Failed to connect to Deepgram: {str(e)}")
        raise Exception(f"Failed to connect to Deepgram: {str(e)}")


async def handle_agent_session(
    client_socket: Any,
    session_id: str,
    on_receive: Callable[[Dict[str, Any]], Any],
    on_send: Callable[[str | bytes], Any]
) -> None:
    """
    Handle a complete agent session with message forwarding between client and Deepgram.
    
    Args:
        client_socket: The client WebSocket connection
        session_id: A unique session identifier
        on_receive: Function to call when receiving a message from client
        on_send: Function to call when sending a message to client
    """
    # Track connection details for debugging
    session_start = time.time()
    messages_from_client = 0
    messages_to_client = 0
    deepgram_socket = None
    
    # Main proxy logic
    try:
        # Connect to Deepgram WebSocket
        deepgram_socket = await connect_to_agent(session_id)
        
        # Forward client messages to Deepgram
        async def forward_client_to_deepgram():
            nonlocal messages_from_client
            try:
                while True:
                    # Get message from client (could be text or binary)
                    message = await on_receive()
                    messages_from_client += 1
                    
                    # Handle different types of messages
                    if "text" in message:
                        # Text message
                        text_message = message["text"]
                        log_message("outgoing", "client → deepgram", text_message)
                        
                        # Forward to Deepgram
                        await deepgram_socket.send(text_message)
                    elif "bytes" in message:
                        # Binary message
                        binary_message = message["bytes"]
                        logger.debug(f"OUTGOING client → deepgram | Binary data: {len(binary_message)} bytes")
                        
                        # Forward binary data to Deepgram
                        await deepgram_socket.send(binary_message)
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
                    
                    # Handle different message types (text or binary)
                    if isinstance(message, str):
                        # Text message
                        log_message("incoming", "deepgram → client", message)
                        
                        # Send text message to client
                        await on_send({"type": "text", "content": message})
                    else:
                        # Binary message (likely audio)
                        logger.debug(f"INCOMING deepgram → client | Binary data: {len(message)} bytes")
                        
                        # Send binary message to client
                        await on_send({"type": "binary", "content": message})
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
        await on_send({"type": "text", "content": error_message})
    
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