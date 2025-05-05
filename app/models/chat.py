"""
Pydantic models for OpenAI Chat Completions API.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, field_validator, model_validator, Field


class ContentItem(BaseModel):
    """Content item in a chat message."""

    type: Literal["text", "image_url"] = "text"
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class ChatMessage(BaseModel):
    """A chat message in a conversation."""

    role: Literal["system", "user", "assistant", "tool", "function"] = "user"
    content: Union[str, List[ContentItem], None] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Dict[str, Any]] = None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        """Convert string content to ContentItem if role is user."""
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            return [
                ContentItem(**item) if isinstance(item, dict) else item for item in v
            ]
        return v

    def model_dump(self, **kwargs):
        """Override model_dump to ensure serializable output"""
        result = {"role": self.role}

        # Handle content field properly
        if self.content is not None:
            if isinstance(self.content, str):
                result["content"] = self.content
            elif isinstance(self.content, list):
                # Convert ContentItem objects to dicts
                content_list = []
                for item in self.content:
                    if hasattr(item, "model_dump"):
                        content_list.append(item.model_dump())
                    else:
                        content_list.append(item)
                result["content"] = content_list

        # Add optional fields if present
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.function_call:
            result["function_call"] = self.function_call

        return result


class ToolParameterProperty(BaseModel):
    """Properties for tool parameters."""

    type: str
    description: Optional[str] = None


class ToolParameters(BaseModel):
    """Parameters for a tool."""

    type: Literal["object"] = "object"
    properties: Dict[str, ToolParameterProperty]
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
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None

    @model_validator(mode="after")
    def validate_tools(self):
        """Validate that tool_choice is valid given tools."""
        if (
            self.tool_choice
            and self.tool_choice != "auto"
            and self.tool_choice != "none"
        ):
            if not self.tools:
                raise ValueError(
                    "tool_choice can only be specified when tools is provided"
                )
        return self


class ToolCallFunction(BaseModel):
    """Function details in a tool call."""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call in a completion response."""

    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ChatCompletionChoice(BaseModel):
    """A choice in a chat completion response."""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class GnosisMetadataItem(BaseModel):
    """A metadata item for internal function or operation tracking."""

    operation_type: str  # "tool_call", "rag", etc.
    name: str  # Function name or operation identifier
    tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class GnosisMetadata(BaseModel):
    """Metadata for Gnosis operations during request processing."""

    operations: List[GnosisMetadataItem] = Field(default_factory=list)
    total_tokens: Optional[int] = None
    total_latency_ms: Optional[float] = None
    summary: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Response from chat completions API."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None
    gnosis_metadata: Optional[GnosisMetadata] = None


class ToolResultMessage(BaseModel):
    """Message with tool results."""

    role: Literal["tool"] = "tool"
    tool_call_id: str
    content: str
