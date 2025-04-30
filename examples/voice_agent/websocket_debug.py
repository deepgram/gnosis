#!/usr/bin/env python3
# websocket_debug.py
# A debug version of the websocket_connect.py example with more error logging

import asyncio
import json
import websockets
import uuid
import traceback

async def connect_to_agent():
    """Connect to a local WebSocket server and send a SettingsConfiguration message."""
    
    uri = "ws://localhost:8080/v1/agent"
    
    # Prepare the SettingsConfiguration message
    settings_config = {
        "type": "SettingsConfiguration",
        "audio": {
            "input": {
                "encoding": "linear16",
                "sample_rate": 44100
            },
            "output": {
                "encoding": "mp3",
                "sample_rate": 24000,
                "bitrate": 48000,
                "container": "none"
            }
        },
        "agent": {
            "listen": {
                "model": "nova-3"
            },
            "think": {
                "provider": {
                    "type": "open_ai"
                },
                "model": "gpt-4o-mini",
                "instructions": "You are a helpful AI assistant. You have a voice and ears, so use them.",
            },
            "speak": {
                "model": "aura-asteria-en"
            }
        },
        "context": {
            "messages": [],
            "replay": False
        }
    }
    
    try:
        print(f"Attempting to connect to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send the SettingsConfiguration message
            print(f"Sending message: {json.dumps(settings_config)[:100]}...")
            await websocket.send(json.dumps(settings_config))
            print("Sent SettingsConfiguration message")
            
            # Wait for the SettingsApplied response
            print("Waiting for response...")
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Keep the connection open for a short time
            await asyncio.sleep(5)
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e.code} {e.reason}")
        print(f"Full error details: {e}")
    except Exception as e:
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(connect_to_agent()) 