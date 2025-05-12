import json
import asyncio
from typing import Any, AsyncGenerator, List

import httpx
from litestar import Router, Request, post
from litestar.exceptions import HTTPException
from litestar.response import Response
from litestar.status_codes import HTTP_502_BAD_GATEWAY, HTTP_501_NOT_IMPLEMENTED

from app.models.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ToolCall,
)
from app.services.openai import OpenAIService
from app.services.tools.registry import get_tool_implementation, execute_tool
from app.services.function_calling import FunctionCallingService
from app.utils.request_helper import RequestHelper


def is_internal(function_name: str) -> bool:
    """
    Check if a function name is internal.
    """
    return function_name.startswith(FunctionCallingService.FUNCTION_PREFIX)


@post("/chat/completions")
async def chat_completion(request: Request, data: ChatCompletionRequest) -> Response:
    """
    Proxy requests to the chat completion API.
    Before sending to the LLM, performs vector search for retrieval augmented generation.
    Also injects tools and processes tool calls if needed.
    """
    request.logger.info(RequestHelper.request_details(request))
    request.logger.debug(RequestHelper.request_dump(request))

    try:
        # Augment chat completion request with RAG context
        # data = RequestAugmentedGenerationService.augment_chat_completion_request(data)

        # Augment the chat completion request with tool calling configuration
        request.logger.info("Setting tool calling configuration")
        data = FunctionCallingService.augment_openai_request(data)

        # We don't support streaming yet
        stream = data.stream or False

        if stream:
            return Response(
                content=json.dumps(
                    {"error": "Streaming response is not supported yet"}
                ),
                status_code=HTTP_501_NOT_IMPLEMENTED,
            )

        # Making the OpenAI request - we don't support streaming yet
        response = await OpenAIService.create_chat_completion(data, stream=False)

        # If we're streaming, return the stream
        if isinstance(response, AsyncGenerator):
            return Response(
                content=json.dumps(
                    {"error": "Streaming response is not supported yet"}
                ),
                status_code=HTTP_501_NOT_IMPLEMENTED,
            )

        # return error from openai
        if response.status_code != 200:
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Content-Type": "application/json"},
            )

        if isinstance(response, Response):
            chat_completion_response = ChatCompletionResponse.model_validate_json(
                response.content
            )

        if (
            hasattr(chat_completion_response, "choices")
            and len(chat_completion_response.choices) > 0
        ):
            choice = chat_completion_response.choices[0]

            if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
                tool_calls = choice.message.tool_calls

                # Separate built-in and user-defined tool calls
                built_in_calls: List[ToolCall] = []
                user_calls: List[ToolCall] = []

                if tool_calls:
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name

                        if tool_call.type == "function" and is_internal(function_name):
                            built_in_calls.append(tool_call)
                        else:
                            user_calls.append(tool_call)

                # If we have built-in calls, process them first
                if built_in_calls:
                    # Create tasks for all built-in tool calls
                    tasks = []
                    for tool_call in built_in_calls:
                        tasks.append(process_built_in_tool_call(tool_call))

                    # Execute all tasks in parallel
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results and add tool call metadata
                    built_in_results = {}

                    for i, result in enumerate(results):
                        tool_call = built_in_calls[i]
                        tool_call_id = tool_call.id

                        built_in_results[tool_call_id] = result

                # If we're returning user-defined tool calls to the client
                if user_calls:
                    # Create a modified response that only includes user tool calls
                    modified_response = chat_completion_response.model_copy()

                    # Replace the tool_calls with only the user-defined ones
                    user_message = choice.message.model_copy()
                    user_message.tool_calls = user_calls

                    # Update the choice with the modified message
                    modified_choice = choice.model_copy()
                    modified_choice.message = user_message

                    # Replace the first choice with our modified choice
                    modified_response.choices = [modified_choice]

                    return Response(
                        content=modified_response.model_dump_json(),
                        status_code=response.status_code,
                        headers={"Content-Type": "application/json"},
                    )
                else:
                    # Create a modified response that has no tool calls
                    modified_response = chat_completion_response.model_copy()

                    # Replace the tool_calls with only the user-defined ones
                    user_message = choice.message.model_copy()
                    del user_message.tool_calls

                    # Update the choice with the modified message
                    modified_choice = choice.model_copy()
                    modified_choice.message = user_message

                    # Replace the first choice with our modified choice
                    modified_response.choices = [modified_choice]

                    return Response(
                        content=modified_response.model_dump_json(),
                        status_code=response.status_code,
                        headers={"Content-Type": "application/json"},
                    )

            return Response(
                content=chat_completion_response.model_dump_json(),
                status_code=response.status_code,
                headers={"Content-Type": "application/json"},
            )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text,
        )
    except TypeError as e:
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=f"JSON serialization error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    # Ensure a response is always returned
    return Response(
        content=json.dumps({"error": "An unexpected error occurred"}),
        status_code=HTTP_502_BAD_GATEWAY,
        headers={"Content-Type": "application/json"},
    )


async def process_built_in_tool_call(tool_call: ToolCall) -> Any:
    """
    Process a built-in tool call.
    """

    try:
        function = tool_call.function
        function_name = function.name

        if not function_name:
            raise ValueError("Tool call missing function name")

        original_name = function_name[len(FunctionCallingService.FUNCTION_PREFIX) :]

        # Parse arguments
        arguments_str = function.arguments

        # Ensure arguments is a string (not a dict)
        if isinstance(arguments_str, dict):
            arguments = arguments_str
        else:
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}

        # Check if the tool exists
        if not get_tool_implementation(original_name):
            raise ValueError(f"Tool '{original_name}' not found")

        return await execute_tool(original_name, arguments)

    except Exception as e:
        # Re-raise the exception to be handled by the caller
        raise e


# Create the router with the handler function
chat_completions_router = Router(
    path="/v1",
    route_handlers=[chat_completion],
    tags=["Chat Completions API"],
)
