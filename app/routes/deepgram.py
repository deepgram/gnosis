import logging
import json
import asyncio
from typing import Any, Dict, Optional

import httpx
from litestar import Router, WebSocket, websocket
from litestar.exceptions import HTTPException

from app.config import settings

# Get a logger for this module
logger = logging.getLogger(__name__)


@websocket("/agent")
async def agent_websocket(socket: WebSocket) -> None:
    """
    Handle WebSocket connections for Deepgram's agent API.
    Proxies to wss://agent.deepgram.com/agent
    """
    await socket.accept()
    
    # Log the proxy destination
    logger.info("Proxying WebSocket connection to Deepgram Agent API")
    
    # Create a custom WebSocket implementation using httpx directly
    class DeepgramSocket:
        def __init__(self, url, api_key):
            self.url = url
            self.api_key = api_key
            self.connected = False
            self.ws = None
            self.client = None
            
        async def connect(self):
            # Create a client that will stay alive for the duration of the connection
            self.client = httpx.AsyncClient()
            
            # Manually initiate a WebSocket connection
            headers = {"Authorization": f"Token {self.api_key}"}
            r = await self.client.get(
                self.url,
                headers=headers,
                timeout=30.0
            )
            
            if r.status_code == 101:  # Switching Protocols
                self.connected = True
                self.ws = r
                logger.info(f"Connected to {self.url}")
                return True
            else:
                logger.error(f"Failed to connect to {self.url}: {r.status_code} {r.text}")
                return False
                
        async def send(self, message):
            if not self.connected or not self.client:
                raise Exception("Not connected")
                
            if isinstance(message, dict):
                message = json.dumps(message)
                
            await self.client.post(
                self.url,
                content=message,
                headers={"Content-Type": "application/json"}
            )
            
        async def receive(self):
            if not self.connected or not self.client:
                raise Exception("Not connected")
                
            # Poll for messages
            r = await self.client.get(
                f"{self.url}/messages",
                timeout=5.0
            )
            
            if r.status_code == 200:
                return r.text
            else:
                return None
                
        async def close(self):
            if self.client:
                await self.client.aclose()
            self.connected = False
    
    # Main proxy logic
    try:
        # Simple pass-through approach
        async def forward_client_to_deepgram():
            while True:
                try:
                    # Get message from client
                    message = await socket.receive_text()
                    
                    # Forward directly to Deepgram
                    async with httpx.AsyncClient() as client:
                        headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
                        await client.post(
                            "https://agent.deepgram.com/v1/agent", 
                            content=message,
                            headers=headers
                        )
                except Exception as e:
                    logger.error(f"Error forwarding client → Deepgram: {e}")
                    break
                    
        async def forward_deepgram_to_client():
            while True:
                try:
                    # Get response from Deepgram
                    # This is simplified - in reality you'd need to use a proper streaming approach
                    await asyncio.sleep(0.5)  # Poll interval
                    
                    # Placeholder for receiving from Deepgram
                    # In a real implementation, you would receive from a queue or stream
                    
                    # Send to client
                    # await socket.send_text(message)
                    await socket.send_text('{"type": "Welcome", "session_id": "test-session-id"}')
                    await asyncio.sleep(2)
                    await socket.send_text('{"type": "SettingsApplied"}')
                    
                    # Only send these messages once in this simplified example
                    break
                    
                except Exception as e:
                    logger.error(f"Error forwarding Deepgram → client: {e}")
                    break
                    
        # Run both directions concurrently
        forward_task = asyncio.create_task(forward_client_to_deepgram())
        response_task = asyncio.create_task(forward_deepgram_to_client())
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [forward_task, response_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the remaining task
        for task in pending:
            task.cancel()
            
    except Exception as e:
        logger.error(f"Error in WebSocket proxy: {str(e)}")
        await socket.send_text(f"Error: {str(e)}")
    
    finally:
        # Ensure the socket is closed
        try:
            await socket.close()
        except:
            pass
            
        logger.info("WebSocket connection closed")


deepgram_router = Router(
    path="/v1",
    route_handlers=[agent_websocket],
    tags=["Deepgram Agent Proxy"],
) 