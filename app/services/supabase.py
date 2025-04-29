"""
Supabase service for interacting with the Supabase API.
"""
import logging
from typing import Optional
from pydantic import BaseModel, Field
from supabase import create_client, Client

from app.config import settings

# Define consistent log format
LOG_FORMAT = '%(levelname)s:     %(message)s'

# Configure module logger with padding
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,  # Consistent format
)

# Get module logger
logger = logging.getLogger(__name__)


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
        logger.debug("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    supabase_client = None


def get_supabase_client() -> Optional[Client]:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The initialized Supabase client or None if not initialized.
    """
    if not config.is_initialized:
        logger.error("Attempting to use uninitialized Supabase client")
    return supabase_client 