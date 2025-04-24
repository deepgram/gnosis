from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.stores.registry import StoreRegistry

from app.config import settings
from app.routes.openai import openai_router
from app.routes.deepgram import deepgram_router
from app.routes.mcp import mcp_router

def create_app() -> Litestar:
    """
    Create and configure the Litestar application.
    """
    cors_config = CORSConfig(
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logging_config = LoggingConfig(
        log_level=settings.LOG_LEVEL,
    )

    openapi_config = OpenAPIConfig(
        title="Gnosis API",
        version=settings.VERSION,
        summary="An intelligence API proxy for OpenAI, Deepgram, and MCP",
        description=(
            "Gnosis works as a proxy to the OpenAI Chat Completion's API, "
            "the Deepgram Voice Agent API, and implements the Model Context Protocol."
        ),
        use_security_scheme=True,
    )

    return Litestar(
        route_handlers=[openai_router, deepgram_router, mcp_router],
        cors_config=cors_config,
        logging_config=logging_config,
        openapi_config=openapi_config,
        debug=settings.DEBUG,
    )

app = create_app() 