import asyncio
import json
from typing import Dict, Any, Tuple, Union, Type
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
    data: Union[str, bytes],
) -> Tuple[bool, Union[BaseAgentMessage, Dict[str, Any], Union[str, bytes]]]:
    """
    Determine if data is binary or text (JSON).
    If it's JSON with a valid "type" field, parse it into the appropriate Pydantic model.

    Args:
        data: Input data, either bytes or string

    Returns:
        Tuple[bool, Union[BaseAgentMessage, Dict, Union[str, bytes]]]: A tuple containing:
            - is_binary: Boolean indicating if the data is binary
            - data: Either the parsed Pydantic model, JSON dict, or the original data
    """

    # Handle dictionary data (like from Litestar WebSocket events)
    if isinstance(data, dict):
        # If it's a unicorn event with a "text" key, extract the text
        if "type" in data and data["type"] == "websocket.receive" and "text" in data:
            data = data["text"]

        # If it's a unicorn event with a "bytes" key, extract the bytes
        elif "type" in data and data["type"] == "websocket.receive" and "bytes" in data:
            data = data["bytes"]

    # If it's already bytes, it's binary
    if isinstance(data, bytes):
        return True, data

    # If it's a string, it's text data (not binary)
    if isinstance(data, str):
        # Try to parse as JSON
        try:
            parsed_data = json.loads(data)
            # Check if it's a valid message with a "type" property
            if isinstance(parsed_data, dict) and "type" in parsed_data:
                message_type = parsed_data["type"]

                # Check if we have a model for this message type
                if message_type in MESSAGE_TYPE_MAP:
                    try:
                        # Try to parse into the correct Pydantic model
                        model_class = MESSAGE_TYPE_MAP[message_type]
                        model_instance = model_class.model_validate(parsed_data)
                        log.debug("Parsed message", type=model_class.__name__)
                        return False, model_instance
                    except Exception as e:
                        log.debug(
                            "Failed to parse message", type=message_type, error=str(e)
                        )
                        # Fall back to returning the dict
                        return False, parsed_data
                else:
                    # Unknown message type
                    log.debug("Unknown message type", type=message_type)
                    return False, parsed_data
            else:
                # It's JSON but not a valid message with type
                log.debug("JSON data without 'type' property")
                # Still return as non-binary but keep as parsed dict
                return False, parsed_data
        except json.JSONDecodeError:
            # Not valid JSON, but still text
            return False, data

    # Fallback (shouldn't reach here)
    log.debug("Unhandled data type", type=str(type(data)))
    return False, None


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
        log.debug(f"Query parameters provided")

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
            data = await client_ws.receive()

            # Extract binary data or JSON text from websocket.receive events
            binary_data = None
            json_text = None

            if (
                isinstance(data, dict)
                and "type" in data
                and data["type"] == "websocket.receive"
            ):
                if "bytes" in data:
                    binary_data = data["bytes"]
                    log.debug(
                        f"CLIENT → PROXY: [Binary data: {len(binary_data)} bytes]"
                    )
                elif "text" in data:
                    json_text = data["text"]
                    truncated = json_text[:50] + ("..." if len(json_text) > 50 else "")
                    log.debug(f"CLIENT → PROXY: {truncated}")

            # Handle websocket events
            if binary_data is not None:
                # If we extracted binary data, forward it directly to Deepgram
                await deepgram_ws.send(binary_data)
                log.debug(f"PROXY → DEEPGRAM: [Binary data: {len(binary_data)} bytes]")
                continue
            elif json_text is not None:
                # If we extracted JSON text, forward it as is
                await deepgram_ws.send(json_text)
                truncated = json_text[:50] + ("..." if len(json_text) > 50 else "")
                log.debug(f"PROXY → DEEPGRAM: {truncated}")
                continue
            elif isinstance(data, dict) and "type" in data:
                event_type = data["type"]

                # Handle websocket.disconnect event
                if event_type == "websocket.disconnect":
                    log.info("Received websocket.disconnect, closing connection")
                    # No need to forward this to Deepgram
                    return

            # Process other types of data (fallback for non-websocket.receive events)
            # Determine if it's binary or text
            is_binary, processed_data = determine_data_type(data)

            if processed_data is None:
                log.debug(f"Could not process data from client")
                continue

            if is_binary:
                # Binary data (audio)
                await deepgram_ws.send(processed_data)
                log.debug(
                    f"PROXY → DEEPGRAM: [Binary data: {len(processed_data) if isinstance(processed_data, bytes) else 'unknown'} bytes]"
                )
            else:
                # Text data - serialize if it's a model, otherwise convert to string
                if isinstance(processed_data, BaseAgentMessage):
                    json_str = processed_data.model_dump_json()
                else:
                    json_str = (
                        json.dumps(processed_data)
                        if isinstance(processed_data, dict)
                        else str(processed_data)
                    )

                truncated = json_str[:50] + ("..." if len(json_str) > 50 else "")
                log.debug(f"PROXY → DEEPGRAM: {truncated}")
                await deepgram_ws.send(json_str)

    except ConnectionClosed as e:
        log.warning(f"Client connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Couldn't forward client to Deepgram: {e}")


async def handle_deepgram_to_client(
    deepgram_ws: websockets.WebSocketClientProtocol, client_ws: WebSocket
) -> None:
    """Processes incoming Deepgram messages and forwards them to client"""
    try:
        while True:
            # Receive message from Deepgram (websockets library uses recv())
            data = await deepgram_ws.recv()

            # Log the message received from Deepgram
            if isinstance(data, bytes):
                log.debug(f"DEEPGRAM → PROXY: [Binary data: {len(data)} bytes]")

                # Forward binary data directly
                await client_ws.send_bytes(data)
                log.debug(f"PROXY → CLIENT: [Binary data: {len(data)} bytes]")
            else:
                # For text data, try to parse it for better logging
                truncated = str(data)[:50] + ("..." if len(str(data)) > 50 else "")
                log.debug(f"DEEPGRAM → PROXY: {truncated}")

                # Forward text data
                await client_ws.send_text(data)
                log.debug(f"PROXY → CLIENT: {truncated}")

                # Check for error message and log it at error level
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and parsed.get("type") == "Error":
                        error_msg = parsed.get(
                            "message", parsed.get("description", "Unknown error")
                        )
                        log.error(f"Received error from Deepgram: {error_msg}")
                except:
                    pass

    except ConnectionClosed as e:
        log.warning(f"Deepgram connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Error forwarding Deepgram to client: {e}")


# Create the router with the handler function
agent_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Voice Agent API"],
)
