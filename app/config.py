import os
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables
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
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    
    # Legacy settings (for backward compatibility)
    MCP_ENABLED: bool = Field(default=False, description="Legacy setting")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()

# Log settings using print
print(f"Settings loaded: "
      f"DEBUG={'✓' if settings.DEBUG else '✗'}, "
      f"LOG_LEVEL={settings.LOG_LEVEL}, "
      f"CORS_ORIGINS={settings.CORS_ORIGINS}, "
      f"OPENAI_API_KEY={'✓' if settings.OPENAI_API_KEY else '✗'}, "
      f"DEEPGRAM_API_KEY={'✓' if settings.DEEPGRAM_API_KEY else '✗'}, "
      f"SUPABASE_URL={'✓' if settings.SUPABASE_URL else '✗'}, "
      f"SUPABASE_KEY={'✓' if settings.SUPABASE_KEY else '✗'}")