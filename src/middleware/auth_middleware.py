from typing import Callable, Awaitable
from litestar.connection import Request
from litestar.middleware import DefineMiddleware
from litestar.exceptions import NotAuthorizedException
from litestar.middleware.base import AbstractMiddleware
from src.services.auth_service import AuthService

class AuthMiddleware(AbstractMiddleware):
    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Request]],
    ) -> Request:
        # Skip authentication for CDN routes
        if request.url.path.startswith('/v1/cdn'):
            return await call_next(request)
        
        is_authenticated = await AuthService.authenticate_request(request)
        if not is_authenticated:
            raise NotAuthorizedException(
                detail='Invalid or missing authentication token',
                headers={'WWW-Authenticate': 'Bearer realm="API"'}
            )
        
        return await call_next(request)

# Create middleware instance for use in app creation
auth_middleware = DefineMiddleware(AuthMiddleware) 