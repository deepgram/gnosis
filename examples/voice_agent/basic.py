#!/usr/bin/env python3
import asyncio
import json
import argparse
import websockets
import colorama
from colorama import Fore, Style
import time

# Initialize colorama for cross-platform color support
colorama.init()

# Global variable to track test status
test_success = True

async def test_agent_proxy(hostname, verbose=False):
    """
    Simple test of the voice agent proxy - connect, send configuration, and handle responses.
    """
    global test_success
    test_success = True  # Reset test status
    
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
        async with websockets.connect(gnosis_url) as websocket:
            # Send settings configuration immediately
            log("Sending SettingsConfiguration message...", "important")
            await websocket.send(json.dumps(settings_config))
            
            # Wait for initial responses
            received_welcome = False
            received_settings_applied = False
            session_id = None
            
            # Try to receive the first few messages
            for _ in range(3):  # Try up to 3 messages
                # Check if we've already received both expected messages
                if received_welcome and received_settings_applied:
                    break
                    
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    
                    # Parse JSON and extract type
                    try:
                        response_data = json.loads(response)
                        msg_type = response_data.get("type", "unknown")
                        
                        # Handle different message types
                        if msg_type == "Welcome":
                            session_id = response_data.get("session_id", "unknown")
                            log(f"✅ Received Welcome message (Session ID: {session_id})", "success")
                            received_welcome = True
                        elif msg_type == "SettingsApplied":
                            log("✅ Received SettingsApplied message", "success")
                            received_settings_applied = True
                        elif msg_type == "Error":
                            error_message = response_data.get("message", "No error message")
                            log(f"❌ Received Error message: {error_message}", "error")
                            test_success = False
                        else:
                            log(f"ℹ️ Received message type: {msg_type}", "info")
                            if verbose:
                                log(f"Full message: {json.dumps(response_data, indent=2)}", "debug")
                    except json.JSONDecodeError:
                        log(f"❌ Could not parse response as JSON: {response}", "error")
                        test_success = False
                
                except asyncio.TimeoutError:
                    log("No more messages received after 3.0 seconds", "warning")
                    break
                except websockets.exceptions.ConnectionClosed as e:
                    if e.code == 1000:
                        log("WebSocket connection closed normally", "info")
                    else:
                        log(f"WebSocket connection closed unexpectedly: {e}", "error")
                        test_success = False
                    break
            
            # Verify that we received expected messages
            if not received_welcome:
                log("❌ Did not receive Welcome message", "error")
                test_success = False
            
            if not received_settings_applied:
                log("❌ Did not receive SettingsApplied message", "error")
                test_success = False
            
            # Continue only if connections still open
            if test_success:
                # Send keep-alive after a delay
                await asyncio.sleep(1)
                log("Sending KeepAlive message...", "info", verbose)
                await websocket.send(json.dumps({"type": "KeepAlive"}))
                
                # Wait briefly for any response to the keep-alive
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    # Try to parse response
                    try:
                        response_data = json.loads(response)
                        msg_type = response_data.get("type", "unknown")
                        log(f"ℹ️ Received message type: {msg_type}", "info", verbose)
                        if verbose:
                            log(f"Full message: {json.dumps(response_data, indent=2)}", "debug")
                    except json.JSONDecodeError:
                        log(f"❌ Could not parse response as JSON: {response}", "error")
                except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                    # No response or already closed, that's okay
                    pass
                
                # Send close message after another delay
                await asyncio.sleep(1)
                log("Sending CloseStream message...", "important")
                
                try:
                    # Send close message
                    await websocket.send(json.dumps({"type": "CloseStream"}))
                    
                    # Wait for the server to close the connection gracefully
                    try:
                        # Try to receive a final message or wait for the connection to close
                        final_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        try:
                            response_data = json.loads(final_response)
                            msg_type = response_data.get("type", "unknown")
                            log(f"ℹ️ Received final message type: {msg_type}", "info")
                        except json.JSONDecodeError:
                            log(f"❌ Could not parse final response as JSON: {final_response}", "error")
                    except websockets.exceptions.ConnectionClosed as e:
                        if e.code == 1000:
                            log("Server closed the connection normally after CloseStream", "important")
                        else:
                            log(f"Server closed the connection with code {e.code}", "warning")
                    except asyncio.TimeoutError:
                        log("No response after CloseStream, closing connection", "info")
                except websockets.exceptions.ConnectionClosed:
                    # Already closed, which is fine
                    log("Connection already closed", "info")
    
    except Exception as e:
        # Check if this is a normal WebSocket closure
        if (isinstance(e, websockets.exceptions.ConnectionClosedOK) or
            isinstance(e, websockets.exceptions.ConnectionClosedError) and 
            (hasattr(e, 'code') and e.code == 1000 or
            "1000" in str(e) or
            "received 1000 (OK)" in str(e))):
            log("WebSocket connection closed normally", "info")
        else:
            log(f"Error in WebSocket connection: {str(e)}", "error")
            test_success = False
    
    # Test summary
    elapsed_time = time.time() - start_time
    log(f"Test completed in {elapsed_time:.2f} seconds", "important")
    if test_success:
        log("✅ TEST PASSED: Successfully connected and communicated with Gnosis Voice Agent", "success")
    else:
        log("❌ TEST FAILED: Issues encountered during the test", "error")

def log(message, level="info", verbose=True):
    """Log a message with appropriate formatting based on importance and verbosity."""
    if level == "debug" and not verbose:
        return
        
    prefix = ""
    
    if level == "error":
        prefix = f"{Fore.RED}ERROR: "
    elif level == "warning":
        prefix = f"{Fore.YELLOW}WARNING: "
    elif level == "success":
        prefix = f"{Fore.GREEN}"
    elif level == "info" and not verbose:
        # Skip info messages unless verbose
        return
    elif level == "debug":
        prefix = f"{Fore.MAGENTA}DEBUG: "
    
    # Apply specific formatting based on message content
    if message.startswith("✅"):
        prefix = f"{Fore.GREEN}"
    elif message.startswith("ℹ️"):
        prefix = f"{Fore.BLUE}"
    elif message.startswith("❌"):
        prefix = f"{Fore.RED}"
        
    print(f"{prefix}{message}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Basic Voice Agent test for Gnosis")
    parser.add_argument("--hostname", default="ws://localhost:8080", 
                        help="Base WebSocket URL (default: ws://localhost:8080)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                        help="Maximum seconds to wait for responses (default: 5)")
    args = parser.parse_args()
    
    print(f"{Style.BRIGHT}{Fore.CYAN}Basic Voice Agent Test{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Hostname:{Style.RESET_ALL} {args.hostname}")
    print(f"{Style.BRIGHT}Timeout:{Style.RESET_ALL} {args.timeout} seconds")
    print(f"{Style.BRIGHT}Verbose:{Style.RESET_ALL} {'Yes' if args.verbose else 'No'}")
    print("═════════════════════════════════════════")
    
    try:
        # Run the test
        asyncio.run(test_agent_proxy(args.hostname, args.verbose))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 