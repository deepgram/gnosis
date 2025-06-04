import json

from litestar.connection import Request


class RequestHelper:
    """Helper class for request handling."""

    @staticmethod
    def request_dump(request: Request) -> str:
        """Get the request details."""
        # Format headers as dict
        headers = dict(request.headers)

        # Build log output
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": headers,
            "query_params": dict(request.query_params),
            "path_params": request.path_params,
        }

        return json.dumps(log_data, indent=2)

    @staticmethod
    def request_details(request: Request) -> str:
        """Get the request details."""

        ip = request.client.host if request.client else "-"
        method = request.method
        path = request.url.path
        http_version = f'HTTP/{request.scope.get("http_version")}'

        return f'{ip} - "{method} {path} {http_version}" Connected'
