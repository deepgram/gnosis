from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    """Capability for a Deepgram agent"""
    type: str
    config: Optional[Dict[str, Any]] = None


class AgentRequest(BaseModel):
    """Request for Deepgram agent"""
    agent_id: str
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    capabilities: Optional[List[AgentCapability]] = None
    config: Optional[Dict[str, Any]] = None 