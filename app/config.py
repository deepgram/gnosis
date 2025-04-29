import os
import logging
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Define consistent log format
LOG_FORMAT = '%(levelname)s:     %(message)s'

# Load environment variables
load_dotenv()

# Configure module logger with padding
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,  # Consistent format
)

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
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    
    # Endpoints
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com")
    DEEPGRAM_BASE_URL: str = Field(default="https://api.deepgram.com")
    
    # Legacy settings (for backward compatibility)
    MCP_ENABLED: bool = Field(default=False, description="Legacy setting")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()

# Log settings
logger = logging.getLogger(__name__)
logger.info(f"Settings loaded: "
            f"DEBUG={'✓' if settings.DEBUG else '✗'}, "
            f"LOG_LEVEL={settings.LOG_LEVEL}, "
            f"CORS_ORIGINS={settings.CORS_ORIGINS}, "
            f"OPENAI_API_KEY={'✓' if settings.OPENAI_API_KEY else '✗'}, "
            f"DEEPGRAM_API_KEY={'✓' if settings.DEEPGRAM_API_KEY else '✗'}, "
            f"SUPABASE_URL={'✓' if settings.SUPABASE_URL else '✗'}, "
            f"SUPABASE_KEY={'✓' if settings.SUPABASE_KEY else '✗'}")