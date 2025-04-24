import os
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # App Settings
    DEBUG: bool = Field(default=False)
    VERSION: str = Field(default="0.1.0")
    LOG_LEVEL: str = Field(default="INFO")
    CORS_ORIGINS: List[str] = Field(default=["*"])
    
    # API Keys
    OPENAI_API_KEY: str = Field(default="")
    DEEPGRAM_API_KEY: str = Field(default="")
    
    # Endpoints
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com")
    DEEPGRAM_BASE_URL: str = Field(default="https://api.deepgram.com")
    
    # Legacy settings (for backward compatibility)
    MCP_ENABLED: bool = Field(default=False, description="Legacy setting")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 