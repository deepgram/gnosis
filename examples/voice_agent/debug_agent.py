#!/usr/bin/env python3
import asyncio
import json
import argparse
import websockets
import colorama
from colorama import Fore, Style
import time
import sys

# Initialize colorama for cross-platform color support
colorama.init()

# Define colors for different message types
COLOR_INFO = Fore.BLUE
COLOR_SEND = Fore.GREEN
COLOR_RECEIVE = Fore.CYAN
COLOR_ERROR = Fore.RED
COLOR_SUCCESS = Fore.GREEN
COLOR_WARNING = Fore.YELLOW
COLOR_DEBUG = Fore.MAGENTA
COLOR_IMPORTANT = Fore.YELLOW + Style.BRIGHT

def log(message, level="info", verbose_only=False):
    """Log a message with appropriate color"""
    if verbose_only and not ARGS.verbose:
        return

    # Select color based on level
    color = {
        "info": COLOR_INFO,
        "send": COLOR_SEND,
        "receive": COLOR_RECEIVE,
        "error": COLOR_ERROR,
        "success": COLOR_SUCCESS,
        "warning": COLOR_WARNING,
        "debug": COLOR_DEBUG,
        "important": COLOR_IMPORTANT
    }.get(level, Fore.WHITE)

    # Print with timestamp
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Style.RESET_ALL}")
    sys.stdout.flush()  # Force flush to ensure output is visible immediately

async def process_message(message, verbose=False):
    """Process and display a message received from the server"""
    try:
        # Try to parse as JSON for better display
        data = json.loads(message)
        msg_type = data.get("type", "unknown")
        
        if msg_type == "AudioMessage":
            # For audio messages, just show type and length to avoid console spam
            audio_len = len(data.get("audio", {}).get("data", ""))
            log(f"← Received AudioMessage ({audio_len} bytes)", "receive")
            if verbose:
                log(f"Audio details: {json.dumps(data.get('audio', {}), indent=2)}", "debug", True)
        else:
            # Print the message type prominently
            log(f"← Received message type: {msg_type}", "receive")
            
            # Show full message in verbose mode
            if verbose:
                log(f"Full message: {json.dumps(data, indent=2)}", "debug", True)
            
            # Parse special message types
            if msg_type == "Welcome":
                session_id = data.get("session_id", "unknown")
                log(f"✅ Connected to session: {session_id}", "success")
            elif msg_type == "SettingsApplied":
                log("✅ Settings successfully applied", "success")
            elif msg_type == "Error":
                error_message = data.get("message", "No error message")
                log(f"❌ Error: {error_message}", "error")
            elif msg_type == "StreamStatusChanged":
                status = data.get("status", "unknown")
                log(f"Stream status changed to: {status}", "important")
            elif msg_type == "SpeechStarted":
                log("🎙️ Speech started", "important")
            elif msg_type == "SpeechFinished":
                log("🎙️ Speech finished", "important")
            elif msg_type == "Transcript":
                transcript = data.get("transcript", {"text": "empty"}).get("text", "empty")
                log(f"📝 Transcript: {transcript}", "important")
            elif msg_type == "IntentResult":
                intent = data.get("intent", {}).get("name", "unknown")
                log(f"🧠 Intent detected: {intent}", "important")
            elif msg_type == "KeepAlive":
                log("♥️ Keep-alive received", "info", True)
    except json.JSONDecodeError:
        # Not JSON - just log as raw text
        log(f"← Received raw message: {message[:100]}...", "receive")

async def debug_agent_proxy(hostname, verbose=False, timeout=15):
    """
    Debug test of the voice agent proxy with detailed message handling
    """
    global test_success
    test_success = True
    
    gnosis_url = f"{hostname}/v1/agent"
    log(f"Connecting to Gnosis Voice Agent proxy at {gnosis_url}...", "important")
    
    # Settings configuration message to send
    settings_config = {
        "type": "SettingsConfiguration",
        "audio": {
            "input": {
                "encoding": "linear16",
                "sample_rate": 24000
            },
            "output": {
                "encoding": "linear16", 
                "sample_rate": 24000,
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
                "model": "gpt-4o-mini"
            },
            "speak": {
                "model": "aura-asteria-en"
            }
        }
    }
    
    start_time = time.time()
    
    try:
        # Connect to WebSocket
        log(f"Opening WebSocket connection...", "info")
        async with websockets.connect(gnosis_url) as websocket:
            log("WebSocket connection established", "success")
            
            # Send settings configuration immediately
            log("→ Sending SettingsConfiguration message...", "send")
            await websocket.send(json.dumps(settings_config))
            
            # Wait for initial responses
            received_welcome = False
            received_settings_applied = False
            
            # Process initial responses (with longer timeout for initial connection)
            initial_timeout = timeout
            
            log(f"Waiting for welcome messages (timeout: {initial_timeout}s)...", "info")
            start_wait = time.time()
            
            try:
                while (time.time() - start_wait) < initial_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        await process_message(response, verbose)
                        
                        # Parse JSON and check message type
                        try:
                            data = json.loads(response)
                            msg_type = data.get("type", "unknown")
                            
                            if msg_type == "Welcome":
                                received_welcome = True
                            elif msg_type == "SettingsApplied":
                                received_settings_applied = True
                            elif msg_type == "Error":
                                log(f"❌ Error received, exiting", "error")
                                return False
                            
                            # If we've received both expected messages, we can continue
                            if received_welcome and received_settings_applied:
                                log("✅ Successfully received welcome and settings confirmation", "success")
                                break
                                
                        except json.JSONDecodeError:
                            pass
                    except asyncio.TimeoutError:
                        # This is expected - we're just polling until we get everything or time out
                        log("Still waiting for responses...", "info", True)
                    except websockets.exceptions.ConnectionClosed as e:
                        log(f"❌ Connection closed unexpectedly (code: {e.code}, reason: {e.reason})", "error")
                        return False
            except Exception as e:
                log(f"❌ Error during initial setup: {e}", "error")
                return False

            # Verify we got the expected messages            
            if not received_welcome or not received_settings_applied:
                missing = []
                if not received_welcome:
                    missing.append("Welcome")
                if not received_settings_applied:
                    missing.append("SettingsApplied")
                log(f"❌ Did not receive required messages: {', '.join(missing)}", "error")
                return False
                
            # Send a keep-alive to check the connection
            log("→ Sending KeepAlive message...", "send")
            await websocket.send(json.dumps({"type": "KeepAlive"}))
            
            # Wait for a bit to receive any responses
            keep_alive_timeout = 5
            log(f"Listening for {keep_alive_timeout} seconds...", "info")
            
            listen_start = time.time()
            try:
                while (time.time() - listen_start) < keep_alive_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        await process_message(response, verbose)
                    except asyncio.TimeoutError:
                        # This is expected during listening period
                        pass
                    except websockets.exceptions.ConnectionClosed as e:
                        log(f"Connection closed (code: {e.code}, reason: {e.reason})", "warning")
                        return True if e.code == 1000 else False
            except Exception as e:
                log(f"Error during listening period: {e}", "error")
                
            # Close connection normally without sending CloseStream
            log("Closing WebSocket connection...", "info")
            await websocket.close(1000, "Normal closure")
            
            # Wait for the server to acknowledge the close
            close_timeout = 5
            log(f"Waiting for connection to close (timeout: {close_timeout}s)...", "info")
            
            close_start = time.time()
            try:
                while (time.time() - close_start) < close_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        await process_message(response, verbose)
                    except asyncio.TimeoutError:
                        # This is expected during closing period
                        pass
                    except websockets.exceptions.ConnectionClosed as e:
                        log(f"Connection closed (code: {e.code}, reason: {e.reason})", "success" if e.code == 1000 else "warning")
                        return True
            except Exception as e:
                log(f"Error during closing sequence: {e}", "error")
                
            log("Closing connection...", "info")
            return True
            
    except websockets.exceptions.InvalidStatusCode as e:
        log(f"❌ Failed to connect: HTTP {e.status_code}", "error")
        return False
    except Exception as e:
        log(f"❌ Error: {e}", "error")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug test for Gnosis Voice Agent Proxy")
    parser.add_argument("--host", type=str, default="ws://localhost:8080", help="Hostname of Gnosis server")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout in seconds for operations")
    
    ARGS = parser.parse_args()
    
    log(f"Debug test for Voice Agent Proxy", "important")
    log(f"Target: {ARGS.host}", "info")
    log(f"Verbose mode: {'Enabled' if ARGS.verbose else 'Disabled'}", "info")
    
    # Run the test
    success = asyncio.run(debug_agent_proxy(ARGS.host, ARGS.verbose, ARGS.timeout))
    
    if success:
        log("✅ Test completed successfully", "success")
        sys.exit(0)
    else:
        log("❌ Test failed", "error")
        sys.exit(1) 