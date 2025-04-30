import asyncio
import json
from typing import Dict, Any, Optional, Tuple, Union, Type
from urllib.parse import urlencode

from litestar import Router, WebSocket, websocket
import websockets
from websockets.exceptions import ConnectionClosed

# Import Pydantic models from agent.py
from app.models.agent import (
    BaseAgentMessage,
    WelcomeMessage,
    SettingsApplied,
    ConversationText,
    FunctionCallResponse,
    KeepAlive,
    SettingsConfiguration,
    Warning,
    Error
)

# Deepgram Agent API endpoint base
DEEPGRAM_AGENT_ENDPOINT = "wss://agent.deepgram.com/agent"

# Note: Deepgram is planning to sunset this API endpoint
# They recommend migrating to v1/agent/converse before May 31st
# See: https://github.com/deepgram/VA-API-Spec-v1

# Map message types to their Pydantic models
MESSAGE_TYPE_MAP: Dict[str, Type[BaseAgentMessage]] = {
    "Welcome": WelcomeMessage,
    "SettingsApplied": SettingsApplied,
    "ConversationText": ConversationText,
    "FunctionCallResponse": FunctionCallResponse,
    "KeepAlive": KeepAlive,
    "SettingsConfiguration": SettingsConfiguration,
    "Warning": Warning,
    "Error": Error
}


def determine_data_type(data: Union[str, bytes]) -> Tuple[bool, Union[BaseAgentMessage, Dict[str, Any], Union[str, bytes]]]:
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
                        print(f"Parsed message as {model_class.__name__}")
                        return False, model_instance
                    except Exception as e:
                        print(f"Failed to parse {message_type} into Pydantic model: {e}")
                        # Fall back to returning the dict
                        return False, parsed_data
                else:
                    # Unknown message type
                    print(f"Unknown message type: {message_type}")
                    return False, parsed_data
            else:
                # It's JSON but not a valid message with type
                print(f"JSON data without 'type' property: {data[:100]}...")
                # Still return as non-binary but keep as parsed dict
                return False, parsed_data
        except json.JSONDecodeError:
            # Not valid JSON, but still text
            return False, data
    
    # Fallback (shouldn't reach here)
    print(f"Unhandled data type: {type(data)}")
    return False, None


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for voice agent API.
    Proxies to Deepgram's agent API.
    """
    await socket.accept()
    print("WebSocket connection accepted")
    
    # Get query parameters from client request and forward them to Deepgram
    query_params = dict(socket.query_params)
    deepgram_url = DEEPGRAM_AGENT_ENDPOINT
    if query_params:
        deepgram_url = f"{DEEPGRAM_AGENT_ENDPOINT}?{urlencode(query_params)}"
    
    # Extract headers that should be forwarded (like authorization)
    headers = {}
    for key, value in socket.headers.items():
        if key.lower() in ['authorization', 'user-agent', 'content-type']:
            headers[key] = value
    
    # Add Deepgram API key header if it's not provided
    if 'authorization' not in [k.lower() for k in headers]:
        from app.config import settings
        if settings.DEEPGRAM_API_KEY:
            headers['Authorization'] = f"Token {settings.DEEPGRAM_API_KEY}"
            print("Added Deepgram API key from settings")
        else:
            print("WARNING: No authorization header provided and DEEPGRAM_API_KEY not set in settings")
    
    # Log the proxy destination
    print(f"Proxying WebSocket connection to voice agent at {deepgram_url}")
    print(f"Using headers: {', '.join(headers.keys())}")
    
    deepgram_ws = None
    # Connect to Deepgram's agent API
    try:
        # Try connecting with additional_headers
        try:
            print("Connecting to Deepgram with additional_headers")
            deepgram_ws = await websockets.connect(deepgram_url, additional_headers=headers)
        except TypeError as e:
            # Fallback to older websockets version that uses extra_headers
            print(f"additional_headers failed: {e}, trying with extra_headers")
            deepgram_ws = await websockets.connect(deepgram_url, extra_headers=headers)
        
        print("Successfully connected to Deepgram agent API")
        
        # Set up tasks for bidirectional message forwarding
        client_to_deepgram_task = asyncio.create_task(handle_client_to_deepgram(socket, deepgram_ws))
        deepgram_to_client_task = asyncio.create_task(handle_deepgram_to_client(deepgram_ws, socket))
        
        # Wait for either task to complete (which means a connection was closed)
        done, pending = await asyncio.wait(
            [client_to_deepgram_task, deepgram_to_client_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Check for exceptions in completed tasks
        for task in done:
            try:
                # This will re-raise any exception that occurred in the task
                task.result()
            except ConnectionClosed as e:
                print(f"WebSocket connection closed: {e.code} {e.reason}")
            except Exception as e:
                print(f"ERROR: Error in forwarding task: {e}")
        
        # Cancel the remaining task
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"ERROR: Error while canceling task: {e}")
        
        print("WebSocket proxy connection closed")
    
    except Exception as e:
        print(f"ERROR: Error in WebSocket proxy: {e}")
        # More detailed exception info
        import traceback
        print(f"ERROR: Exception details: {traceback.format_exc()}")
    finally:
        # Ensure both connections are closed
        if deepgram_ws:
            try:
                # Use close() instead of checking closed attribute
                await deepgram_ws.close()
                print("Deepgram WebSocket connection closed")
            except Exception as e:
                print(f"ERROR: Error closing Deepgram WebSocket: {e}")
        
        try:
            await socket.close()
            print("Client WebSocket connection closed")
        except Exception as e:
            print(f"ERROR: Error closing client WebSocket: {e}")


async def handle_client_to_deepgram(client_ws: WebSocket, deepgram_ws: websockets.WebSocketClientProtocol) -> None:
    """Processes incoming client messages, potentially modifying them, and forwards to Deepgram. Manages disconnects by closing connections."""
    try:
        while True:
            # Receive message from client - using receive() for Litestar WebSocket
            data = await client_ws.receive()
            
            print(f"Received message from client: {data}")
            
            # Handle internal Litestar/Uvicorn websocket events
            if isinstance(data, dict) and "type" in data:
                event_type = data["type"]
                
                # Handle websocket.disconnect event
                if event_type == "websocket.disconnect":
                    print("Received websocket.disconnect, closing connection")
                    # No need to forward this to Deepgram
                    return
                
                # Handle other internal events as needed
                if event_type.startswith("websocket."):
                    print(f"Handling internal websocket event: {event_type}")
                    continue  # Skip forwarding internal events

            # Determine if it's a known message type
            is_binary, processed_data = determine_data_type(data)
            
            if processed_data is None:
                print(f"ERROR: Could not process data from client: {str(data)[:100]}...")
                continue
                
            if is_binary:
                # Binary data (audio)
                await deepgram_ws.send(processed_data)
                print("Forwarded binary data from client to Deepgram")
            elif isinstance(processed_data, BaseAgentMessage):
                # Known message type
                json_str = processed_data.model_dump_json()
                await deepgram_ws.send(json_str)
                print(f"Forwarded {processed_data.__class__.__name__} from client to Deepgram")
            else:
                # Unknown text data, don't forward
                print(f"ERROR: Received unknown data from client: {str(data)[:100]}...")
    
    except ConnectionClosed as e:
        print(f"Client connection closed: {e.code} {e.reason}")
        raise
    except Exception as e:
        print(f"ERROR: Error forwarding client to Deepgram: {e}")
        import traceback
        print(f"ERROR: Exception details: {traceback.format_exc()}")
        raise


async def handle_deepgram_to_client(deepgram_ws: websockets.WebSocketClientProtocol, client_ws: WebSocket) -> None:
    """Processes incoming Deepgram messages, potentially modifying them, responding to them or forwarding them to client"""
    try:
        while True:
            # Receive message from Deepgram (websockets library uses recv())
            data = await deepgram_ws.recv()
            
            print(f"Received message from Deepgram: {data}")
            
            # Handle internal control events if present
            if isinstance(data, dict) and "type" in data:
                event_type = data["type"]
                
                # Handle any internal control events
                if event_type.startswith("websocket."):
                    print(f"Handling internal websocket event from Deepgram: {event_type}")
                    continue  # Skip forwarding internal events
            
            # Determine message type
            is_binary, processed_data = determine_data_type(data)
            
            if processed_data is None:
                print(f"ERROR: Could not process data from Deepgram: {str(data)[:100]}...")
                continue
                
            if is_binary:
                # Binary data (audio)
                await client_ws.send_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
                print("Forwarded binary data from Deepgram to client")
            elif isinstance(processed_data, BaseAgentMessage):
                # Known message type
                json_str = processed_data.model_dump_json()
                await client_ws.send_text(json_str)
                print(f"Forwarded {processed_data.__class__.__name__} from Deepgram to client")
            else:
                # Unknown text data, don't forward
                print(f"ERROR: Received unknown data from Deepgram: {str(data)[:100]}...")
    
    except ConnectionClosed as e:
        print(f"WARNING: Deepgram connection closed: {e.code} {e.reason}")
        import traceback
        print(f"ERROR: Exception details: {traceback.format_exc()}")
        raise
    except Exception as e:
        print(f"ERROR: Error forwarding Deepgram to client: {e}")
        import traceback
        print(f"ERROR: Exception details: {traceback.format_exc()}")
        raise


# Create the router with the handler function
agent_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Voice Agent API"],
) 