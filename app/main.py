import os
import uvicorn
import structlog
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from litestar.handlers import get
from litestar.connection import Request
from uuid import uuid4

from app.config import settings
from app.routes.chat_completions import chat_completions_router
from app.routes.agent import agent_router


async def before_request_handler(request: Request) -> None:
    request_id = str(uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for the server."""
    return {"status": "ok"}


def create_app() -> Litestar:
    """
    Create and configure the Litestar application.
    """
    # Log settings after structured logging is set up
    log = structlog.get_logger()

    # Convert sensitive fields to truncated versions
    settings_dict = {}
    for key, value in settings.model_dump().items():
        if (
            isinstance(value, str)
            and any(
                x in key.lower() for x in ["key", "secret", "password", "token", "url"]
            )
            and len(value) > 10
        ):
            settings_dict[key] = f"{value[:10]}..."
        else:
            settings_dict[key] = value

    log.info("Application settings", **settings_dict)

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

    return Litestar(
        route_handlers=[health_check, chat_completions_router, agent_router],
        cors_config=cors_config,
        openapi_config=openapi_config,
        debug=settings.DEBUG,
        logging_config=None,  # Don't configure logging here
        before_request=before_request_handler,
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
        log_config=None,  # <-- disables Uvicorn's logging override
    )
