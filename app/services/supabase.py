"""
Supabase service for interacting with the Supabase API.
"""
import logging
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

# Initialize Supabase client
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    logger.debug("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    # Create a dummy client to avoid errors
    supabase = None

def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The initialized Supabase client.
    """
    if supabase is None:
        logger.error("Attempting to use uninitialized Supabase client")
    return supabase 