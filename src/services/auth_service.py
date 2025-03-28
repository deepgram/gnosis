from typing import Optional, Tuple, Dict, Any
import httpx
from litestar.connection import Request
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_401_UNAUTHORIZED

class AuthService:
    @staticmethod
    def extract_token_from_header(auth_header: Optional[str]) -> Optional[Tuple[str, str]]:
        if not auth_header:
            return None
            
        parts = auth_header.strip().split(' ')
        if len(parts) != 2 or parts[0].lower() not in ['token', 'bearer']:
            return None
            
        return (parts[0].lower(), parts[1])
    
    @staticmethod
    def extract_token_from_websocket_protocol(protocol_header: Optional[str]) -> Optional[Tuple[str, str]]:
        if not protocol_header:
            return None
            
        protocols = [p.strip() for p in protocol_header.split(',')]
        if len(protocols) != 2 or protocols[0].lower() not in ['token', 'bearer']:
            return None
            
        return (protocols[0].lower(), protocols[1])
    
    @staticmethod
    async def verify_token(schema: str, token: str) -> Dict[Any, Any]:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"{schema.capitalize()} {token}"}
            response = await client.get("https://api.deepgram.com/v1/projects", headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code or HTTP_401_UNAUTHORIZED,
                    detail=f"Authentication failed: {response.text}"
                )
                
            return response.json()

    @staticmethod
    async def authenticate_request(request: Request) -> bool:
        # Check Authorization header first
        auth_header = request.headers.get('Authorization')
        auth_data = AuthService.extract_token_from_header(auth_header)
        
        # If no Authorization header, check WebSocket protocol
        if not auth_data:
            ws_protocol = request.headers.get('Sec-WebSocket-Protocol')
            auth_data = AuthService.extract_token_from_websocket_protocol(ws_protocol)
        
        if not auth_data:
            return False
            
        schema, token = auth_data
        try:
            await AuthService.verify_token(schema, token)
            return True
        except HTTPException:
            return False 