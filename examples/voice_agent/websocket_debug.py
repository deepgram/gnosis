#!/usr/bin/env python3
# websocket_debug.py
# A debug version of the websocket_connect.py example with more error logging

import asyncio
import json
import websockets
import uuid
import traceback
import signal

# Global flag to track if we should exit
should_exit = False

def handle_interrupt():
    """Handle keyboard interrupt (Ctrl+C)"""
    global should_exit
    should_exit = True
    print("\nReceived interrupt signal. Closing connection...")

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
            
            print("Listening for messages (press Ctrl+C to exit)...")
            
            # Set up signal handling for graceful exit
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, handle_interrupt)
            
            # Continuously listen for messages until interrupted
            message_counter = 0
            while not should_exit:
                try:
                    # Wait for a message with a timeout to check for exit flag
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    message_counter += 1
                    
                    # Try to parse JSON for prettier display
                    try:
                        parsed = json.loads(response)
                        print(f"\nMessage {message_counter}:")
                        print(f"Type: {parsed.get('type', 'Unknown')}")
                        print(json.dumps(parsed, indent=2))
                    except json.JSONDecodeError:
                        # Not JSON, just print as-is (might be binary data)
                        print(f"\nMessage {message_counter} (non-JSON):")
                        print(f"Length: {len(response)} bytes")
                        # Print beginning of the message if it's text
                        if isinstance(response, str):
                            print(f"Preview: {response[:100]}...")
                        else:
                            print(f"Binary data received")
                
                except asyncio.TimeoutError:
                    # Just a timeout to check the exit flag, not an error
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"WebSocket connection closed: {e.code} {e.reason}")
                    break
            
            print(f"Connection closing. Received {message_counter} messages total.")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed with error: {e.code} {e.reason}")
        print(f"Full error details: {e}")
    except Exception as e:
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(connect_to_agent()) 