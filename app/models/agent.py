"""
Pydantic models for agent-related functionality.

This module contains models for working with the Deepgram Voice Agent API V1.
No backward compatibility with early access API is provided.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal, Union
from app.models.chat import GnosisMetadataItem


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

    encoding: str = "linear16"
    sample_rate: int = 24000
    container: str = "none"
    bitrate: Optional[int] = None

    class Config:
        extra = "allow"


class AudioConfig(BaseModel):
    """Audio configuration for the agent."""

    input: Optional[AudioInputConfig] = None
    output: Optional[AudioOutputConfig] = None

    class Config:
        extra = "allow"


class ListenProviderConfig(BaseModel):
    """Provider configuration for listen capability."""

    type: str = "deepgram"
    model: str = "nova-3"
    keyterms: Optional[List[str]] = None

    class Config:
        extra = "allow"


class ListenConfig(BaseModel):
    """Configuration for agent listening."""

    provider: ListenProviderConfig = ListenProviderConfig()

    class Config:
        extra = "allow"


class ThinkProviderConfig(BaseModel):
    """Provider configuration for think capability."""

    type: str = "open_ai"
    model: Optional[str] = None
    temperature: float = 0.7
    endpoint: Optional[str] = None

    class Config:
        extra = "allow"


class ThinkConfig(BaseModel):
    """Configuration for agent thinking."""

    provider: ThinkProviderConfig = ThinkProviderConfig()
    prompt: Optional[str] = None
    functions: Optional[Dict[str, Dict[str, Any]]] = None
    endpoint: Optional[str] = None

    class Config:
        extra = "allow"


class SpeakProviderConfig(BaseModel):
    """Provider configuration for speak capability."""

    type: str = "deepgram"
    model: str = "aura-2-andromeda-en"
    voice: Optional[Union[str, Dict[str, Any]]] = None
    model_id: Optional[str] = None
    language: Optional[str] = None
    language_code: Optional[str] = None

    class Config:
        extra = "allow"


class SpeakConfig(BaseModel):
    """Configuration for agent speech."""

    provider: SpeakProviderConfig = SpeakProviderConfig()
    endpoint: Optional[str] = None

    class Config:
        extra = "allow"


class AgentConfig(BaseModel):
    """Configuration for a voice agent."""

    language: str = "en"
    listen: Optional[ListenConfig] = None
    think: Optional[ThinkConfig] = None
    speak: Optional[SpeakConfig] = None
    greeting: Optional[str] = None

    class Config:
        extra = "allow"


class ContextConfig(BaseModel):
    """Configuration for agent context."""

    messages: List[Dict[str, Any]] = []
    replay: bool = False

    class Config:
        extra = "allow"


class Settings(BaseAgentMessage):
    """Configure the voice agent and sets the input and output audio formats."""

    type: Literal["Settings"] = "Settings"
    mip_opt_out: bool = False
    experimental: bool = False
    audio: AudioConfig
    agent: AgentConfig
    context: Optional[ContextConfig] = None

    class Config:
        extra = "allow"


class UpdateSpeak(BaseAgentMessage):
    """Update the agent's speaking configuration."""

    type: Literal["UpdateSpeak"] = "UpdateSpeak"
    speak: SpeakConfig

    class Config:
        extra = "allow"


class InjectAgentMessage(BaseAgentMessage):
    """Inject a message into the agent's conversation."""

    type: Literal["InjectAgentMessage"] = "InjectAgentMessage"
    content: str
    role: str = "user"

    class Config:
        extra = "allow"


class AgentKeepAlive(BaseAgentMessage):
    """Keep-alive message sent by the client."""

    type: Literal["AgentKeepAlive"] = "AgentKeepAlive"

    class Config:
        extra = "allow"


class FunctionCall(BaseAgentMessage):
    """Function call request from Deepgram."""

    type: Literal["FunctionCall"] = "FunctionCall"
    function_name: str
    function_call_id: str
    arguments: Union[str, Dict[str, Any]]

    class Config:
        extra = "allow"


class FunctionCallFunction(BaseModel):
    """Individual function in a FunctionCallRequest"""

    id: str
    name: str
    arguments: str
    client_side: bool

    class Config:
        extra = "allow"


class FunctionCallRequest(BaseAgentMessage):
    """Function call request in new format with client_side flag."""

    type: Literal["FunctionCallRequest"] = "FunctionCallRequest"
    functions: List[FunctionCallFunction]

    class Config:
        extra = "allow"


class FunctionCallResponse(BaseAgentMessage):
    """Function call response message."""

    type: Literal["FunctionCallResponse"] = "FunctionCallResponse"
    id: str
    name: str
    content: str

    class Config:
        extra = "allow"


class WelcomeMessage(BaseAgentMessage):
    """Welcome message from the server."""

    type: Literal["Welcome"] = "Welcome"
    request_id: str

    class Config:
        extra = "allow"


class SettingsApplied(BaseAgentMessage):
    """Confirmation that settings were applied."""

    type: Literal["SettingsApplied"] = "SettingsApplied"

    class Config:
        extra = "allow"


class UserStartedSpeaking(BaseAgentMessage):
    """Notification that the user has started speaking."""

    type: Literal["UserStartedSpeaking"] = "UserStartedSpeaking"

    class Config:
        extra = "allow"


class ConversationText(BaseAgentMessage):
    """Conversation text message."""

    type: Literal["ConversationText"] = "ConversationText"
    role: str
    content: str

    class Config:
        extra = "allow"


class AgentThinking(BaseAgentMessage):
    """Notification that the agent is thinking."""

    type: Literal["AgentThinking"] = "AgentThinking"

    class Config:
        extra = "allow"


class PromptUpdated(BaseAgentMessage):
    """Notification that the prompt has been updated."""

    type: Literal["PromptUpdated"] = "PromptUpdated"

    class Config:
        extra = "allow"


class SpeakUpdated(BaseAgentMessage):
    """Notification that the speak configuration has been updated."""

    type: Literal["SpeakUpdated"] = "SpeakUpdated"

    class Config:
        extra = "allow"


class AgentAudioDone(BaseAgentMessage):
    """Agent audio done message."""

    type: Literal["AgentAudioDone"] = "AgentAudioDone"

    class Config:
        extra = "allow"


class KeepAlive(BaseAgentMessage):
    """Keep-alive message from the server."""

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
    description: Optional[str] = None
    message: Optional[str] = None  # For backward compatibility with existing code
    code: Optional[str] = None

    class Config:
        extra = "allow"


class GnosisMetadataMessage(BaseAgentMessage):
    """Metadata about Gnosis operations during request processing."""

    type: Literal["GnosisMetadata"] = "GnosisMetadata"
    operations: List[GnosisMetadataItem] = []
    total_tokens: Optional[int] = None
    total_latency_ms: Optional[float] = None
    summary: Optional[str] = None

    class Config:
        extra = "allow"
