#!/usr/bin/env python3
# websocket_debug.py
# A simple WebSocket client that connects to an agent, listens for messages, and responds based on mappings

import asyncio
import json
import websockets
import signal
import traceback

# Global flag to track if we should exit
should_exit = False

def handle_interrupt():
    """Handle keyboard interrupt (Ctrl+C)"""
    global should_exit
    should_exit = True
    print("\nReceived interrupt signal. Closing connection...")

# Message mapping - defines what to send when specific message types are received
MESSAGE_MAPPINGS = {
    "Welcome": {
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
}

async def connect_to_agent():
    """Connect to a WebSocket server, listen for messages, and respond based on mappings."""
    
    uri = "ws://localhost:8080/v1/agent"
    
    try:
        print(f"Attempting to connect to {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
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
                    
                    # Try to parse JSON
                    try:
                        message = json.loads(response)
                        message_type = message.get("type", "Unknown")
                        
                        # Log received message
                        print(f"\nReceived message {message_counter}:")
                        print(f"Type: {message_type}")
                        print(json.dumps(message, indent=2))
                        
                        # Check if we have a mapping for this message type
                        if message_type in MESSAGE_MAPPINGS:
                            response_message = MESSAGE_MAPPINGS[message_type]
                            if response_message is not None:
                                print(f"\nSending response to {message_type}:")
                                print(json.dumps(response_message, indent=2))
                                await websocket.send(json.dumps(response_message))
                            else:
                                print(f"No response needed for {message_type}")
                        else:
                            print(f"No mapping defined for message type: {message_type}")
                    
                    except json.JSONDecodeError:
                        # Not JSON, just print as-is
                        print(f"\nMessage {message_counter} (non-JSON):")
                        print(f"Length: {len(response)} bytes")
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