from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ChatCompletionMessageContent(BaseModel):
    """Content for system response"""
    type: str
    text: Optional[str] = None


class ChatCompletionMessage(BaseModel):
    """Message in a chat completion"""
    role: str
    content: Optional[Union[str, List[ChatCompletionMessageContent]]] = None
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionFunctionCall(BaseModel):
    """Function call parameters"""
    name: str
    arguments: str


class ChatCompletionToolCall(BaseModel):
    """Tool call parameters"""
    id: str
    type: str
    function: ChatCompletionFunctionCall


class ChatCompletionFunction(BaseModel):
    """Function definition"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ChatCompletionTool(BaseModel):
    """Tool definition"""
    type: str
    function: ChatCompletionFunction


class ChatCompletionRequest(BaseModel):
    """Request for chat completion"""
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    functions: Optional[List[ChatCompletionFunction]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[ChatCompletionTool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None

    @model_validator(mode="after")
    def validate_functions_and_tools(self):
        """Validate that both functions and tools are not provided simultaneously"""
        if self.functions and self.tools:
            raise ValueError("Cannot provide both 'functions' and 'tools' parameters")
        if self.function_call and self.tool_choice:
            raise ValueError("Cannot provide both 'function_call' and 'tool_choice' parameters")
        return self


class ChatCompletionChoice(BaseModel):
    """Choice in a chat completion response"""
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Response from chat completion"""
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Dict[str, int]] = None 