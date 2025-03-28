from litestar import Router, get
from litestar.response import Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from src.services.cdn_service import CDNService

@get("/cdn/widget.js")
async def handle_widget_js() -> Response:
    """Handle requests for the widget JavaScript file"""
    try:
        js_content = CDNService.get_widget_js()
        return Response(
            content=js_content,
            media_type="application/javascript",
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except Exception as e:
        return Response(
            content={'error': str(e)},
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )

# Create router for CDN
cdn_router = Router(path="/v1", route_handlers=[handle_widget_js]) 