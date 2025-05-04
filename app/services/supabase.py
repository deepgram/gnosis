"""
Supabase service for interacting with the Supabase API.
"""
import structlog
from typing import Optional
from pydantic import BaseModel, Field
from supabase import create_client, Client

from app.config import settings

log = structlog.get_logger()
class SupabaseConfig(BaseModel):
    """
    Configuration for the Supabase client.
    """
    url: str
    key: str
    is_initialized: bool = Field(default=False)


# Global configuration
config = SupabaseConfig(
    url=settings.SUPABASE_URL,
    key=settings.SUPABASE_KEY
)

# Initialize Supabase client
supabase_client: Optional[Client] = None
try:
    if config.url and config.key:
        supabase_client = create_client(config.url, config.key)
        config.is_initialized = True
        log.info("Supabase client initialized successfully")
except Exception as e:
    log.error("Failed to initialize Supabase client", error=e)
    supabase_client = None


def get_supabase_client() -> Optional[Client]:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The initialized Supabase client or None if not initialized.
    """
    if not config.is_initialized:
        log.error("Attempting to use uninitialized Supabase client")
    return supabase_client 