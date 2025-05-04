"""
Pydantic models for agent-related functionality.

This module contains models for working with the Deepgram Voice Agent API.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal, Union


class BaseAgentMessage(BaseModel):
    """Base class for all agent messages."""
    type: str


class AudioInputConfig(BaseModel):
    """Audio input configuration settings."""
    encoding: str = "linear16"
    sample_rate: int = 24000

    class Config:
        extra = "allow"


class AudioOutputConfig(BaseModel):
    """Audio output configuration settings."""
    encoding: str = "mp3"
    sample_rate: int = 24000
    bitrate: Optional[int] = None
    container: Optional[str] = None

    class Config:
        extra = "allow"


class AudioConfig(BaseModel):
    """Audio configuration for the agent."""
    input: Optional[AudioInputConfig] = None
    output: Optional[AudioOutputConfig] = None

    class Config:
        extra = "allow"


class ListenConfig(BaseModel):
    """Configuration for agent listening."""
    model: str = "nova-3"

    class Config:
        extra = "allow"


class ProviderConfig(BaseModel):
    """Provider configuration for think capability."""
    type: str = "openai"

    class Config:
        extra = "allow"


class ThinkConfig(BaseModel):
    """Configuration for agent thinking."""
    provider: Optional[ProviderConfig] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    functions: Optional[Dict[str, Dict[str, Any]]] = None

    class Config:
        extra = "allow"


class SpeakConfig(BaseModel):
    """Configuration for agent speech."""
    model: str = "aura-asteria-en"

    class Config:
        extra = "allow"


class AgentConfig(BaseModel):
    """Configuration for a voice agent."""
    listen: Optional[ListenConfig] = None
    think: Optional[ThinkConfig] = None
    speak: Optional[SpeakConfig] = None

    class Config:
        extra = "allow"


class ContextConfig(BaseModel):
    """Configuration for agent context."""
    messages: List[Dict[str, Any]] = []
    replay: bool = False

    class Config:
        extra = "allow"


class SettingsConfiguration(BaseAgentMessage):
    """Configure the voice agent and sets the input and output audio formats."""
    type: Literal["SettingsConfiguration"] = "SettingsConfiguration"
    audio: AudioConfig
    agent: AgentConfig
    context: Optional[ContextConfig] = None

    class Config:
        extra = "allow"


# Function call message
class FunctionCall(BaseAgentMessage):
    """Function call request from Deepgram."""
    type: Literal["FunctionCall"] = "FunctionCall"
    function_name: str
    function_call_id: str
    arguments: Union[str, Dict[str, Any]]

    class Config:
        extra = "allow"


# Response messages
class WelcomeMessage(BaseAgentMessage):
    """Welcome message from the server."""
    type: Literal["Welcome"] = "Welcome"
    session_id: str

    class Config:
        extra = "allow"


class SettingsApplied(BaseAgentMessage):
    """Confirmation that settings were applied."""
    type: Literal["SettingsApplied"] = "SettingsApplied"

    class Config:
        extra = "allow"


class ConversationText(BaseAgentMessage):
    """Conversation text message."""
    type: Literal["ConversationText"] = "ConversationText"
    role: str
    content: str

    class Config:
        extra = "allow"


class FunctionCallResponse(BaseAgentMessage):
    """Function call response message."""
    type: Literal["FunctionCallResponse"] = "FunctionCallResponse"
    function_call_id: str
    output: str

    class Config:
        extra = "allow"


class KeepAlive(BaseAgentMessage):
    """Keep-alive message."""
    type: Literal["KeepAlive"] = "KeepAlive"

    class Config:
        extra = "allow"


class Warning(BaseAgentMessage):
    """Warning message from Deepgram."""
    type: Literal["Warning"] = "Warning"
    description: str
    code: Optional[str] = None

    class Config:
        extra = "allow"


class Error(BaseAgentMessage):
    """Error message from Deepgram."""
    type: Literal["Error"] = "Error"
    description: Optional[str] = None  # For v1 API
    message: Optional[str] = None      # For legacy API
    code: Optional[str] = None

    class Config:
        extra = "allow"