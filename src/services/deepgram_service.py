import websockets
from websockets.client import WebSocketClientProtocol
from src.config import Config
from typing import Tuple, Optional

class DeepgramService:
    @staticmethod
    async def create_websocket_connection(auth_token: Optional[str] = None) -> Tuple[WebSocketClientProtocol, WebSocketClientProtocol]:
        """
        Create a WebSocket connection to Deepgram's API
        
        Args:
            auth_token: The validated token to use for authentication. If not provided, falls back to Config.DEEPGRAM_API_KEY
            
        Returns:
            Tuple of (WebSocket connection, WebSocket connection)
            
        Raises:
            Exception: If connection fails
        """
        try:
            token = auth_token or Config.DEEPGRAM_API_KEY
            ws = await websockets.connect(
                'wss://api.deepgram.com/v1/agent',
                extra_headers={'Authorization': f'Token {token}'}
            )
            return ws, ws
        except Exception:
            raise 