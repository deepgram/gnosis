import asyncio
from litestar import Router, websocket
from litestar.connection import WebSocket
from litestar.exceptions import WebSocketDisconnect
from src.services.deepgram_service import DeepgramService
from src.services.auth_service import AuthService

@websocket("/agent")
async def handle_deepgram_websocket(socket: WebSocket) -> None:
    """Handle WebSocket connections to Deepgram's voice agent service"""
    await socket.accept()
    
    # Extract token from the request
    auth_header = socket.scope.get("headers", {}).get(b"authorization", b"").decode()
    auth_data = AuthService.extract_token_from_header(auth_header)
    
    # If no Authorization header, check WebSocket protocol
    if not auth_data:
        ws_protocol = socket.scope.get("headers", {}).get(b"sec-websocket-protocol", b"").decode()
        auth_data = AuthService.extract_token_from_websocket_protocol(ws_protocol)
    
    # Use the extracted token
    auth_token = auth_data[1] if auth_data else None
    
    deepgram_ws, session = await DeepgramService.create_websocket_connection(auth_token)
    
    try:
        async def forward_to_client():
            while True:
                try:
                    message = await deepgram_ws.receive()
                    if message["type"] == "text":
                        await socket.send_text(message["data"])
                    elif message["type"] == "bytes":
                        await socket.send_bytes(message["data"])
                    elif message["type"] in ("close", "error"):
                        await socket.close()
                        break
                except Exception:
                    await socket.close()
                    break

        async def forward_to_deepgram():
            while True:
                try:
                    message = await socket.receive()
                    if message["type"] == "websocket.receive":
                        if "text" in message:
                            await deepgram_ws.send_text(message["text"])
                        elif "bytes" in message:
                            await deepgram_ws.send_bytes(message["bytes"])
                    elif message["type"] == "websocket.disconnect":
                        await deepgram_ws.close()
                        break
                except WebSocketDisconnect:
                    await deepgram_ws.close()
                    break
                except Exception:
                    await deepgram_ws.close()
                    break

        await asyncio.gather(
            forward_to_client(),
            forward_to_deepgram()
        )
    finally:
        await session.close()

# Create router for websocket
deepgram_router = Router(path="/v1", route_handlers=[handle_deepgram_websocket]) 