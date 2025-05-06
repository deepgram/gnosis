import asyncio
import json
from typing import Dict, Tuple, Type
from urllib.parse import urlencode

from litestar import Router, WebSocket, websocket
import structlog
import websockets
from websockets.exceptions import ConnectionClosed

# Import Pydantic models from agent.py
from app.models.agent import (
    BaseAgentMessage,
    WelcomeMessage,
    SettingsApplied,
    ConversationText,
    FunctionCallResponse,
    FunctionCall,
    KeepAlive,
    SettingsConfiguration,
    Warning,
    Error,
    GnosisMetadataMessage,
)

# Initialize logger
log = structlog.get_logger()

# Deepgram Agent API endpoint base
DEEPGRAM_AGENT_ENDPOINT = "wss://agent.deepgram.com/agent"

# Map message types to their Pydantic models
MESSAGE_TYPE_MAP: Dict[str, Type[BaseAgentMessage]] = {
    "Welcome": WelcomeMessage,
    "SettingsApplied": SettingsApplied,
    "ConversationText": ConversationText,
    "FunctionCall": FunctionCall,
    "FunctionCallResponse": FunctionCallResponse,
    "KeepAlive": KeepAlive,
    "SettingsConfiguration": SettingsConfiguration,
    "Warning": Warning,
    "Error": Error,
    "GnosisMetadata": GnosisMetadataMessage,
}


def determine_data_type(
    data: str,
) -> Tuple[str, BaseAgentMessage]:
    """
    Determine if data is a valid JSON string and validate it against known message types in MESSAGE_TYPE_MAP.

    Args:
        data: Input data as a string

    Returns:
        Tuple[str, BaseAgentMessage]: A tuple containing:
            - message_type: The type of the validated message
            - model_instance: A validated BaseAgentMessage object
            
    Raises:
        ValueError: If the data cannot be parsed as a valid message type
    """
    # If it's a string, try to parse it as JSON
    if isinstance(data, str):
        try:
            parsed_data = json.loads(data)
            
            # Check if it's a valid message with a "type" property
            if isinstance(parsed_data, dict) and "type" in parsed_data:
                message_type = parsed_data["type"]

                # Validate against known message types
                if message_type in MESSAGE_TYPE_MAP:
                    try:
                        # Parse into the correct Pydantic model
                        model_class = MESSAGE_TYPE_MAP[message_type]
                        model_instance = model_class.model_validate(parsed_data)
                        log.debug(f"Parsed message as {model_class.__name__}")
                        return message_type, model_instance
                    except Exception as e:
                        # Failed to validate with the model
                        log.error(f"Failed to validate message as {message_type}: {str(e)}")
                        raise ValueError(f"Message validation failed for type {message_type}: {str(e)}")
                else:
                    # Unknown message type
                    log.error(f"Unknown message type: {message_type}")
                    raise ValueError(f"Unknown message type: {message_type}")
            else:
                # Missing 'type' field
                log.error("JSON message missing 'type' field")
                raise ValueError("JSON message missing required 'type' field")
        except json.JSONDecodeError as e:
            # Invalid JSON
            log.error(f"Invalid JSON: {str(e)}")
            raise ValueError(f"Cannot parse as JSON: {str(e)}")


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for voice agent API.
    Proxies to Deepgram's agent API.
    """
    await socket.accept()
    log.info("WebSocket connection accepted from client")

    # Get query parameters from client request and forward them to Deepgram
    query_params = dict(socket.query_params)
    deepgram_url = DEEPGRAM_AGENT_ENDPOINT
    if query_params:
        deepgram_url = f"{DEEPGRAM_AGENT_ENDPOINT}?{urlencode(query_params)}"
        log.debug("Query parameters provided")

    # Extract headers that should be forwarded (like authorization)
    headers = {}
    for key, value in socket.headers.items():
        if key.lower() in ["authorization", "user-agent", "content-type"]:
            headers[key] = value

    # Add Deepgram API key header if it's not provided
    if "authorization" not in [k.lower() for k in headers]:
        from app.config import settings

        if settings.DEEPGRAM_API_KEY:
            headers["Authorization"] = f"Token {settings.DEEPGRAM_API_KEY}"
            log.debug("Using Deepgram API key from environment")
        else:
            log.warning(
                "No authorization header provided and DEEPGRAM_API_KEY not set in settings"
            )

    # Log the proxy destination
    log.info(f"Connecting to Deepgram: {deepgram_url}")

    deepgram_ws = None
    # Connect to Deepgram's agent API
    try:
        deepgram_ws = await websockets.connect(deepgram_url, additional_headers=headers)

        log.info("Successfully connected to Deepgram agent API")

        # Set up tasks for bidirectional message forwarding
        client_to_deepgram_task = asyncio.create_task(
            handle_client_to_deepgram(socket, deepgram_ws)
        )
        deepgram_to_client_task = asyncio.create_task(
            handle_deepgram_to_client(deepgram_ws, socket)
        )

        # Wait for either task to complete (which means a connection was closed)
        done, pending = await asyncio.wait(
            [client_to_deepgram_task, deepgram_to_client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Check for exceptions in completed tasks
        for task in done:
            try:
                # This will re-raise any exception that occurred in the task
                task.result()
            except ConnectionClosed as e:
                log.error(f"WebSocket connection closed: {e.code} {e.reason}")
            except Exception as e:
                log.error(f"Error in forwarding task: {e}")

        # Cancel the remaining task
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                log.debug("Task was cancelled successfully")
            except Exception as e:
                log.error(f"Error while canceling task: {e}")

        log.info("WebSocket proxy connection closed")

    except Exception as e:
        log.error(f"Error in WebSocket proxy: {e}")
    finally:
        # Ensure both connections are closed
        if deepgram_ws:
            try:
                await deepgram_ws.close()
                log.info("Deepgram WebSocket connection closed")
            except Exception as e:
                log.error(f"Error closing Deepgram WebSocket: {e}")

        try:
            await socket.close()
            log.info("Client WebSocket connection closed")
        except Exception as e:
            log.error(f"Error closing client WebSocket: {e}")


async def handle_client_to_deepgram(
    client_ws: WebSocket, deepgram_ws: websockets.WebSocketClientProtocol
) -> None:
    """Processes incoming client messages and forwards to Deepgram. Manages disconnects by closing connections."""
    try:
        while True:
            # Receive message from client - using receive() for Litestar WebSocket
            message = await client_ws.receive()
            
            # Handle websocket.disconnect event
            if isinstance(message, dict) and message.get("type") == "websocket.disconnect":
                log.info("Received websocket.disconnect, closing connection")
                return
                
            # Extract data from Litestar WebSocket message format
            binary_data = None
            text_data = None
            
            if isinstance(message, dict) and message.get("type") == "websocket.receive":
                # Extract binary or text data from the message
                if "bytes" in message:
                    binary_data = message["bytes"]
                elif "text" in message:
                    text_data = message["text"]
            
            # Handle binary data (audio)
            if binary_data is not None:
                log.debug(f"CLIENT → PROXY: [Binary data: {len(binary_data)} bytes]")
                await deepgram_ws.send(binary_data)
                log.debug(f"PROXY → DEEPGRAM: [Binary data: {len(binary_data)} bytes]")
                continue
                
            # Handle text data (JSON messages)
            if text_data is not None:
                # Try to use determine_data_type to parse the message
                try:
                    message_type, model_instance = determine_data_type(text_data)
                    
                    # Check if it's a SettingsConfiguration message
                    if isinstance(model_instance, SettingsConfiguration):
                        log.debug("Intercepted SettingsConfiguration message")
                        
                        # Augment with our function definitions
                        from app.services.function_calling import FunctionCallingService
                        
                        # Log the original settings
                        original_config = model_instance.model_dump(exclude_none=True)
                        log.debug(f"Original settings: {json.dumps(original_config, indent=2)}")
                        
                        augmented_config = FunctionCallingService.augment_deepgram_agent_config(
                            original_config
                        )
                        
                        # Log the augmented settings
                        log.debug(f"Augmented settings: {json.dumps(augmented_config, indent=2)}")
                        
                        # Log the functions specifically to debug the format
                        if ("agent" in augmented_config and "think" in augmented_config["agent"] and 
                                "functions" in augmented_config["agent"]["think"]):
                            functions = augmented_config["agent"]["think"]["functions"]
                            log.debug(f"Functions format: {type(functions).__name__}")
                            log.debug(f"Functions: {json.dumps(functions, indent=2)}")
                        
                        # Convert back to JSON string
                        text_data = json.dumps(augmented_config)
                        log.debug("Augmented SettingsConfiguration with function definitions")
                    else:
                        # It's a validated message but not SettingsConfiguration
                        # Just convert it to JSON and forward
                        text_data = model_instance.model_dump_json()
                        
                    truncated = text_data[:50] + ("..." if len(text_data) > 50 else "")
                    log.debug(f"CLIENT → PROXY: {truncated}")
                    
                    # Forward the message to Deepgram
                    await deepgram_ws.send(text_data)
                    log.debug(f"PROXY → DEEPGRAM: {truncated}")
                    
                except ValueError as e:
                    # determine_data_type couldn't validate the message
                    log.warning(f"Message validation failed: {str(e)}")
                    # Forward as raw text anyway, as it might be a valid but unknown message type
                    await deepgram_ws.send(text_data)
                    log.debug("Forwarded unvalidated message to Deepgram")
                    
                continue
                
            # If we get here, it means we couldn't handle the message format
            log.warning(f"Unrecognized message format: {message}")
            
    except ConnectionClosed as e:
        log.warning(f"Client connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Couldn't forward client to Deepgram: {e}")


async def handle_deepgram_to_client(
    deepgram_ws: websockets.WebSocketClientProtocol, 
    client_ws: WebSocket
) -> None:
    """Processes incoming Deepgram messages and forwards them to client."""
    try:
        while True:
            # Receive message from Deepgram
            data = await deepgram_ws.recv()
            
            # Handle binary data (audio)
            if isinstance(data, bytes):
                log.debug(f"DEEPGRAM → PROXY: [Binary data: {len(data)} bytes]")
                await client_ws.send_bytes(data)
                log.debug(f"PROXY → CLIENT: [Binary data: {len(data)} bytes]")
                continue
                
            # Handle text data (messages)
            # For text data, try to parse it for better logging
            truncated = str(data)[:50] + ("..." if len(str(data)) > 50 else "")
            log.debug(f"DEEPGRAM → PROXY: {truncated}")

            # Forward text data
            await client_ws.send_text(data)
            log.debug(f"PROXY → CLIENT: {truncated}")
                
    except ConnectionClosed as e:
        log.warning(f"Deepgram connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Error in deepgram_to_client: {e}")


# Create the router with the handler function
agent_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Voice Agent API"],
)
