import os
import uvicorn
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from litestar.handlers import get
from litestar.logging import LoggingConfig
from app.config import settings
from app.routes.chat_completions import chat_completions_router
from app.routes.agent import agent_router
import logging


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for the server."""
    return {"status": "ok"}


def create_app() -> Litestar:
    """
    Create and configure the Litestar application.
    """

    cors_config = CORSConfig(
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    openapi_config = OpenAPIConfig(
        title="Gnosis API",
        version=settings.VERSION,
        summary="An intelligence API proxy for LLMs and voice agents",
        description=(
            "Gnosis works as a proxy to the Chat Completion's API and "
            "the Voice Agent API, adding tools and RAG capabilities."
        ),
    )

    # Define the formatter
    log_formatter = logging.Formatter("%(levelname)s:\t  %(message)s")

    # Create a StreamHandler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    # Define Litestar's logging configuration to use the *class* of the handler
    # and then we will manually add the *instance* later.
    logging_config = LoggingConfig(
        root={
            "level": settings.LOG_LEVEL.upper() or "DEBUG",
            "handlers": ["shared_console"],
        },
        formatters={"standard": {"format": "%(levelname)s:\t  %(message)s"}},
        handlers={
            "shared_console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
            }
        },
    )

    # Configure standard Python logging to use the shared handler
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper() or "DEBUG")
    root_logger.addHandler(console_handler)

    return Litestar(
        route_handlers=[health_check, chat_completions_router, agent_router],
        cors_config=cors_config,
        openapi_config=openapi_config,
        debug=settings.DEBUG,
        logging_config=logging_config,
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
    )
