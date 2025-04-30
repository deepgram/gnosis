import os
import uvicorn
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from litestar.handlers import get

from app.config import settings
from app.routes.chat_completions import chat_completions_router
from app.routes.agent import agent_router

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

    return Litestar(
        route_handlers=[health_check, chat_completions_router, agent_router],
        cors_config=cors_config,
        openapi_config=openapi_config,
        debug=settings.DEBUG,
    )

app = create_app()

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    
    print(f"Settings loaded: "
          f"DEBUG={'✓' if settings.DEBUG else '✗'}, "
          f"LOG_LEVEL={settings.LOG_LEVEL}, "
          f"CORS_ORIGINS={settings.CORS_ORIGINS}, "
          f"OPENAI_API_KEY={'✓' if settings.OPENAI_API_KEY else '✗'}, "
          f"DEEPGRAM_API_KEY={'✓' if settings.DEEPGRAM_API_KEY else '✗'}, "
          f"SUPABASE_URL={'✓' if settings.SUPABASE_URL else '✗'}, "
          f"SUPABASE_KEY={'✓' if settings.SUPABASE_KEY else '✗'}")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
    ) 