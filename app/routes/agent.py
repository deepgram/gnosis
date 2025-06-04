import asyncio
import json
import time
from typing import Dict, Type, List, Any
from urllib.parse import urlencode

from litestar import Router, WebSocket, websocket
import structlog
import websockets
from websockets.exceptions import ConnectionClosed
from websockets import ClientConnection

# Import Pydantic models from agent.py
from app.models.agent import (
    BaseAgentMessage,
    WelcomeMessage,
    SettingsApplied,
    ConversationText,
    FunctionCallResponse,
    FunctionCallRequest,
    FunctionCallFunction,
    KeepAlive,
    Settings,
    Warning,
    Error,
    AgentAudioDone,
    UpdateSpeak,
    InjectAgentMessage,
    AgentKeepAlive,
    UserStartedSpeaking,
    AgentThinking,
    PromptUpdated,
    SpeakUpdated,
)

from app.services.function_calling import FunctionCallingService
from app.services.tools.registry import get_tool_implementation, execute_tool

# Initialize logger
log = structlog.get_logger()

# Deepgram Agent API endpoint base
DEEPGRAM_AGENT_ENDPOINT = "wss://agent.deepgram.com/v1/agent/converse"

# Map message types to their Pydantic models
MESSAGE_TYPE_MAP: Dict[str, Type[BaseAgentMessage]] = {
    # Server response messages
    "Welcome": WelcomeMessage,
    "SettingsApplied": SettingsApplied,
    "ConversationText": ConversationText,
    "UserStartedSpeaking": UserStartedSpeaking,
    "AgentThinking": AgentThinking,
    "AgentAudioDone": AgentAudioDone,
    "PromptUpdated": PromptUpdated,
    "SpeakUpdated": SpeakUpdated,
    "KeepAlive": KeepAlive,
    "Warning": Warning,
    "Error": Error,
    # Client request messages
    "Settings": Settings,
    "UpdateSpeak": UpdateSpeak,
    "InjectAgentMessage": InjectAgentMessage,
    "AgentKeepAlive": AgentKeepAlive,
    # Function calling messages (only new format)
    "FunctionCallRequest": FunctionCallRequest,
    "FunctionCallResponse": FunctionCallResponse,
}


def determine_data_type(
    data: str,
) -> BaseAgentMessage:
    """
    Determine if data is a valid JSON string and validate it against known message types in MESSAGE_TYPE_MAP.

    Args:
        data: Input data as a string

    Returns:
        BaseAgentMessage: A validated BaseAgentMessage object

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
                        return model_instance
                    except Exception as e:
                        # Failed to validate with the model
                        log.error(
                            f"Failed to validate message as {message_type}: {str(e)}"
                        )
                        raise ValueError(
                            f"Message validation failed for type {message_type}: {str(e)}"
                        )
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


async def process_agent_tool_call(
    function_call: FunctionCallFunction,
) -> Dict[str, Any]:
    """
    Process a Deepgram agent function call for built-in tools.

    Args:
        function_call: The FunctionCallFunction object from Deepgram

    Returns:
        Dict containing the result of the tool call and function call ID
    """
    function_id = function_call.id
    function_name = function_call.name

    try:
        # Extract the original name without the prefix
        original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX) :]
        log.debug(f"Processing built-in agent tool: {function_name} → {original_name}")

        # Parse arguments
        arguments = {}
        try:
            arguments = json.loads(function_call.arguments)
        except json.JSONDecodeError:
            log.warning(f"Invalid JSON in tool arguments: {function_call.arguments}")

        # Log function call start
        log.info(
            f"🔧 AGENT FUNCTION CALL START - Executing {original_name} with ID {function_id}"
        )

        # Call the tool
        execution_start_time = time.time()
        result = await execute_tool(original_name, arguments)
        execution_duration_ms = (time.time() - execution_start_time) * 1000

        # Log function call completion
        log.info(
            f"🔧 AGENT FUNCTION CALL COMPLETE - "
            f"{original_name} executed in {execution_duration_ms:.2f}ms"
        )

        return {
            "function_id": function_id,
            "result": result,
            "duration_ms": execution_duration_ms,
            "name": original_name,
            "function_name": function_name,
            "arguments": arguments,
        }
    except Exception as e:
        log.error(f"Error processing agent tool call: {e}")
        return {
            "function_id": function_id,
            "error": str(e),
            "name": original_name if "original_name" in locals() else function_name,
            "function_name": function_name,
        }


def separate_function_calls(
    function_calls: List[FunctionCallFunction],
) -> Dict[str, List[FunctionCallFunction]]:
    """
    Sort incoming function calls into built-in Gnosis functions, user-defined functions, and Deepgram internal functions.

    Args:
        function_calls: List of FunctionCallFunction objects from the request

    Returns:
        Dict with categorized function calls
    """
    result = {
        "client_side_built_in": [],  # client_side: true, Gnosis built-in functions
        "client_side_user_defined": [],  # client_side: true, user-defined functions
        "server_side": [],  # client_side: false functions (Deepgram internal)
    }

    for func in function_calls:
        if not func.client_side:
            # This is a Deepgram internal function call (client_side: false)
            result["server_side"].append(func)
            continue

        # This is a client_side: true function, check if it's built-in to Gnosis
        function_name = func.name
        is_built_in = function_name.startswith(FunctionCallingService.FUNCTION_PREFIX)

        if is_built_in:
            # Check if it's a valid built-in function
            original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX) :]
            has_implementation = get_tool_implementation(original_name) is not None

            if has_implementation:
                result["client_side_built_in"].append(func)
            else:
                # It's a built-in function pattern but doesn't exist in our registry
                # Treat as user-defined
                log.warning(
                    f"Unknown built-in function: {original_name}, treating as user-defined"
                )
                result["client_side_user_defined"].append(func)
        else:
            # Regular user-defined function
            result["client_side_user_defined"].append(func)

    return result


async def process_built_in_function_calls(
    built_in_calls: List[FunctionCallFunction],
    deepgram_ws: ClientConnection,
    client_ws: WebSocket,
):
    """
    Process multiple built-in function calls in parallel and send responses to Deepgram and client.

    Args:
        built_in_calls: List of FunctionCallFunction objects to process
        deepgram_ws: WebSocket connection to Deepgram
        client_ws: WebSocket connection to the client
    """
    if not built_in_calls:
        return

    # Log start of parallel processing
    call_count = len(built_in_calls)
    if call_count > 1:
        log.info(f"🔄 Processing {call_count} built-in agent tool calls in parallel")

    # Create tasks for all built-in function calls
    tasks = [process_agent_tool_call(call) for call in built_in_calls]

    # Execute all tasks in parallel
    start_time = time.time()
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    total_duration_ms = (time.time() - start_time) * 1000

    # Log completion of parallel execution
    if call_count > 1:
        log.info(
            f"🔄 Completed {call_count} parallel agent tool calls in {total_duration_ms:.2f}ms"
        )

    # Filter out exceptions and only keep successful results
    valid_results: List[Dict[str, Any]] = []
    for res in raw_results:
        if isinstance(res, Exception):
            log.error(f"Error processing agent tool call: {str(res)}")
        else:
            # Explicit cast to help the linter
            valid_results.append(res)  # type: ignore

    # Process successful results and send responses back to Deepgram and client
    for result in valid_results:
        try:
            # Extract values from the result dictionary
            function_id = result["function_id"]
            function_name = result["function_name"]
            result["name"]
            output_result = result.get("result", {})

            # Format the output as a string
            output_str = json.dumps(output_result)

            # Create response for Deepgram
            response = FunctionCallResponse(
                type="FunctionCallResponse",
                id=function_id,
                name=function_name,
                content=output_str,
            )

            # Send response to Deepgram
            response_json = response.model_dump_json()
            log.debug(
                f"Sending function call response to Deepgram: {response_json[:50]}..."
            )
            await deepgram_ws.send(response_json)

            # Also send response to client (marked as internal)
            await client_ws.send_text(response_json)

        except Exception as e:
            log.error(f"Error sending function call response: {str(e)}")


@websocket("/agent/converse")
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

    deepgram_ws: ClientConnection | None = None
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
    client_ws: WebSocket, deepgram_ws: ClientConnection
) -> None:
    """Processes incoming client messages and forwards to Deepgram. Manages disconnects by closing connections."""
    try:
        while True:
            # Receive message from client - using receive() for Litestar WebSocket
            message = await client_ws.receive()

            # Handle websocket.disconnect event
            if (
                isinstance(message, dict)
                and message.get("type") == "websocket.disconnect"
            ):
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
                # Try to parse and process the message
                try:
                    # Use determine_data_type to parse the message
                    model_instance = determine_data_type(text_data)

                    # Special handling for specific message types we support
                    if isinstance(model_instance, Settings):
                        log.debug("Intercepted Settings message")

                        # Augment with our function definitions
                        from app.services.function_calling import FunctionCallingService

                        # Log the original settings
                        original_config = model_instance.model_dump(exclude_none=True)
                        log.debug(
                            f"Original settings: {json.dumps(original_config, indent=2)}"
                        )

                        augmented_config = (
                            FunctionCallingService.augment_deepgram_agent_config(
                                original_config
                            )
                        )

                        # Log the augmented settings
                        log.debug(
                            f"Augmented settings: {json.dumps(augmented_config, indent=2)}"
                        )

                        # Convert back to JSON string
                        text_data = json.dumps(augmented_config)
                        log.debug("Augmented Settings with function definitions")

                    # Forward the message (original or modified) to Deepgram
                    truncated = text_data[:50] + ("..." if len(text_data) > 50 else "")
                    log.debug(f"CLIENT → PROXY: {truncated}")
                    await deepgram_ws.send(text_data)
                    log.debug(f"PROXY → DEEPGRAM: {truncated}")

                except ValueError as e:
                    # determine_data_type couldn't validate the message
                    # This could be a legacy message or an invalid message
                    log.debug(f"Unrecognized message format: {str(e)}")

                    # Forward to Deepgram anyway and let it handle any errors
                    await deepgram_ws.send(text_data)

                continue

            # If we get here, it means we couldn't handle the message format
            log.warning(f"Unrecognized message format: {message}")

    except ConnectionClosed as e:
        log.warning(f"Client connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Couldn't forward client to Deepgram: {e}")


async def handle_deepgram_to_client(
    deepgram_ws: ClientConnection, client_ws: WebSocket
) -> None:
    """Processes incoming Deepgram messages and forwards them to client."""
    try:
        async for message in deepgram_ws:
            # Handle different message types (bytes or string)
            if isinstance(message, bytes):
                # Binary data like audio
                log.debug(f"Received binary data from Deepgram: {len(message)} bytes")
                await client_ws.send_bytes(message)
                continue

            # Text data - convert to string if it's not already
            if isinstance(message, str):
                data_str = message
            elif isinstance(message, bytes):
                data_str = message.decode("utf-8")
            elif isinstance(message, memoryview):
                data_str = bytes(message).decode("utf-8")
            else:
                data_str = str(message)  # Fallback

            # Log received message (only first part for potentially large data)
            if len(data_str) > 100:
                log.debug(f"Received from Deepgram: {data_str[:100]}...")
            else:
                log.debug(f"Received from Deepgram: {data_str}")

            # Try to parse the message
            try:
                model_instance = determine_data_type(data_str)

                # Handle only FunctionCallRequest in the new format
                if isinstance(model_instance, FunctionCallRequest):
                    log.debug("Intercepted FunctionCallRequest message")

                    # Separate function calls into different categories
                    categorized_calls = separate_function_calls(
                        model_instance.functions
                    )

                    # Process built-in Gnosis functions (client_side: true, Gnosis functions)
                    if categorized_calls["client_side_built_in"]:
                        log.info(
                            f"Processing {len(categorized_calls['client_side_built_in'])} built-in function calls"
                        )
                        # Process built-in function calls in the background
                        asyncio.create_task(
                            process_built_in_function_calls(
                                categorized_calls["client_side_built_in"],
                                deepgram_ws,
                                client_ws,
                            )
                        )

                    # Forward user-defined client_side: true functions to client
                    if categorized_calls["client_side_user_defined"]:
                        log.info(
                            f"Forwarding {len(categorized_calls['client_side_user_defined'])} user-defined client-side function calls"
                        )
                        # Create a new request with only the user-defined functions
                        user_request = FunctionCallRequest(
                            type="FunctionCallRequest",
                            functions=categorized_calls["client_side_user_defined"],
                        )
                        user_request_json = user_request.model_dump_json()
                        await client_ws.send_text(user_request_json)

                    # Forward server-side functions to client (for visibility)
                    if categorized_calls["server_side"]:
                        count = len(categorized_calls["server_side"])
                        log.info(f"Forwarding {count} " f"server-side function calls")
                        server_request = FunctionCallRequest(
                            type="FunctionCallRequest",
                            functions=categorized_calls["server_side"],
                        )
                        server_request_json = server_request.model_dump_json()
                        await client_ws.send_text(server_request_json)

                    # Skip default forwarding since we've handled all cases
                    continue

                # All other recognized message types are forwarded as-is

            except ValueError as e:
                # This could be a legacy message format or invalid message
                # Just log it and forward without modification
                log.debug(f"Unrecognized message format from Deepgram: {str(e)}")

            # Forward message to client without modification
            if isinstance(message, str):
                await client_ws.send_text(message)
            else:
                await client_ws.send_bytes(message)
    except ConnectionClosed as e:
        log.error(f"Deepgram WebSocket connection closed: {e.code} {e.reason}")
    except Exception as e:
        log.error(f"Error in Deepgram to client communication: {e}")


# Create the router with the handler function
agent_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Voice Agent API"],
)
