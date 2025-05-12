"""
Pydantic models for OpenAI Chat Completions API.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel

Role = Literal["system", "user", "assistant", "tool", "function"]


## Chat Completion Request


class ContentItem(BaseModel):
    """Content item in a chat message."""

    type: Literal["text", "image_url"] = "text"
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class ChatMessage(BaseModel):
    """A chat message in a conversation."""

    role: Role
    content: Union[str, List[ContentItem], None] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Dict[str, Any]] = None


class ToolParameterProperty(BaseModel):
    """Properties for tool parameters."""

    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


class ToolParameters(BaseModel):
    """Parameters for a tool."""

    type: Literal["object"] = "object"
    properties: Dict[str, ToolParameterProperty]  # Allow arbitrary property objects
    required: Optional[List[str]] = None


class ToolFunction(BaseModel):
    """Function definition for a tool."""

    name: str
    description: str
    parameters: ToolParameters


class Tool(BaseModel):
    """Tool definition for the OpenAI API."""

    type: Literal["function"] = "function"
    function: ToolFunction


class ChatCompletionRequest(BaseModel):
    """Request body for chat completions API."""

    model: str
    messages: List[ChatMessage]
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[Literal["auto", "none"], Dict[str, Any]]] = None
    stream: Optional[bool] = False

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


## Chat Completion Response


class ToolCallFunction(BaseModel):
    """Function in a tool call."""

    name: str
    arguments: str

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


class ToolCall(BaseModel):
    """Tool call in a chat completion choice."""

    id: str
    type: str
    function: ToolCallFunction

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


class ChoiceMessage(BaseModel):
    """Message in a chat completion choice."""

    content: Optional[str] = None
    role: Role
    tool_calls: Optional[List[ToolCall]] = None

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


class ChatCompletionChoice(BaseModel):
    """Choice in a chat completion."""

    message: ChoiceMessage

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields


class ChatCompletionResponse(BaseModel):
    """Response body for chat completions API."""

    choices: List[ChatCompletionChoice]

    model_config = {"extra": "allow"}  # Allow arbitrary additional fields
