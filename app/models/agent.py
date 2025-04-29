"""
Pydantic models for Deepgram Voice Agent API.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message types for agent API."""
    AUDIO = "Audio"
    CONFIG = "Config"
    TRANSCRIPT = "Transcript"
    SPEECH = "Speech"
    THINKING = "Thinking"
    FINISHED = "Finished" 
    ERROR = "Error"


class AgentConfig(BaseModel):
    """Configuration for the agent API."""
    api_key: Optional[str] = None
    model: str
    voice: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    language: Optional[str] = "en-US"
    end_utterance_silence: Optional[float] = 0.5
    query_params: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    continue_conversation: Optional[bool] = True


class AudioMessage(BaseModel):
    """Audio message from client to agent."""
    type: Literal[MessageType.AUDIO] = MessageType.AUDIO
    audio: str  # base64 encoded audio data


class ConfigMessage(BaseModel):
    """Configuration message from client to agent."""
    type: Literal[MessageType.CONFIG] = MessageType.CONFIG
    config: AgentConfig


class TranscriptMessage(BaseModel):
    """Transcript message from agent to client."""
    type: Literal[MessageType.TRANSCRIPT] = MessageType.TRANSCRIPT
    text: str
    is_final: bool = False


class SpeechMessage(BaseModel):
    """Speech message from agent to client."""
    type: Literal[MessageType.SPEECH] = MessageType.SPEECH
    audio: str  # base64 encoded audio data
    is_final: bool = False


class ThinkingMessage(BaseModel):
    """Thinking message from agent to client."""
    type: Literal[MessageType.THINKING] = MessageType.THINKING
    text: Optional[str] = None


class FinishedMessage(BaseModel):
    """Finished message from agent to client."""
    type: Literal[MessageType.FINISHED] = MessageType.FINISHED


class ErrorMessage(BaseModel):
    """Error message from agent to client."""
    type: Literal[MessageType.ERROR] = MessageType.ERROR
    message: str


ClientMessage = Union[AudioMessage, ConfigMessage]
AgentMessage = Union[TranscriptMessage, SpeechMessage, ThinkingMessage, FinishedMessage, ErrorMessage] 