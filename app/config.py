from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables before everything else
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # App Settings
    DEBUG: bool = Field(default=False)
    VERSION: str = Field(default="0.1.0")
    LOG_LEVEL: str = Field(default="DEBUG")
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # API Keys
    OPENAI_API_KEY: str = Field(default="")
    DEEPGRAM_API_KEY: str = Field(default="")
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")

    # Legacy settings (for backward compatibility)
    MCP_ENABLED: bool = Field(default=False, description="Legacy setting")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


# Initialize settings
settings = Settings()
