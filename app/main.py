import logging
import os
import uvicorn
import sys  # Import sys for stdout
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.handlers import get

from app.config import settings
from app.routes.openai import openai_router
from app.routes.deepgram import deepgram_router

# Define consistent log format
LOG_FORMAT = '%(levelname)s:     %(message)s'

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,  # Added padding after colon
)

# Get application logger
logger = logging.getLogger(__name__)

@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for the server."""
    return {"status": "ok"}

def create_app() -> Litestar:
    """
    Create and configure the Litestar application.
    """
    # Log external services initialization
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        logger.info("Supabase client initialized")
    else:
        logger.warning("Supabase configuration missing or incomplete")
        
    cors_config = CORSConfig(
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure logging based on the LOG_LEVEL setting
    logging_config = LoggingConfig(
        # Configure Litestar logging
        root={"level": settings.LOG_LEVEL, "handlers": ["console"]},
        formatters={
            "default": {
                "fmt": LOG_FORMAT,  # Use consistent format
            }
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        loggers={
            "uvicorn": {"level": settings.LOG_LEVEL, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": settings.LOG_LEVEL, "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": settings.LOG_LEVEL, "handlers": ["console"], "propagate": False},
        },
        log_exceptions="always",
    )

    openapi_config = OpenAPIConfig(
        title="Gnosis API",
        version=settings.VERSION,
        summary="An intelligence API proxy for OpenAI and Deepgram",
        description=(
            "Gnosis works as a proxy to the OpenAI Chat Completion's API and "
            "the Deepgram Voice Agent API."
        ),
    )

    return Litestar(
        route_handlers=[health_check, openai_router, deepgram_router],
        cors_config=cors_config,
        logging_config=logging_config,
        openapi_config=openapi_config,
        debug=settings.DEBUG,
    )

app = create_app()

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    ) 