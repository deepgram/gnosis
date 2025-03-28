from litestar import Litestar
from litestar.openapi import OpenAPIConfig
from litestar.config.cors import CORSConfig

from src.handlers.openai_handler import openai_router
from src.handlers.deepgram_handler import deepgram_router
from src.handlers.cdn_handler import cdn_router
from src.middleware.auth_middleware import auth_middleware

def create_app() -> Litestar:
    """Create and configure the Litestar application."""
    
    # Configure CORS
    cors_config = CORSConfig(
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Configure OpenAPI
    openapi_config = OpenAPIConfig(
        title="Gnosis API",
        version="1.0.0",
        description="A unified API gateway that enhances AI interactions with contextual knowledge.",
        use_handler_docstrings=True,
    )
    
    # Create the Litestar application with all routers and middleware
    app = Litestar(
        route_handlers=[openai_router, deepgram_router, cdn_router],
        middleware=[auth_middleware],
        cors_config=cors_config,
        openapi_config=openapi_config,
    )
    
    return app 