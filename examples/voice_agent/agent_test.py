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

async def test_agent_proxy(hostname, verbose=False, timeout=5):
    """
    Advanced test of the voice agent proxy with proper message handling and error management.
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
    
    try:
        # Connect to WebSocket
        async with websockets.connect(gnosis_url) as websocket:
            # Send settings configuration immediately
            log("Sending SettingsConfiguration message...", "important")
            await websocket.send(json.dumps(settings_config))
            
            # Wait for initial responses
            start_time = time.time()
            received_welcome = False
            received_settings_applied = False
            session_id = None
            
            # Process initial responses
            try:
                for _ in range(3):  # Try to receive up to 3 messages
                    # Check if we've already received both expected messages
                    if received_welcome and received_settings_applied:
                        break
                        
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        await process_message(response, verbose)
                        
                        # Parse JSON and update status flags
                        try:
                            data = json.loads(response)
                            msg_type = data.get("type", "unknown")
                            
                            if msg_type == "Welcome":
                                received_welcome = True
                                session_id = data.get("session_id", "unknown")
                            elif msg_type == "SettingsApplied":
                                received_settings_applied = True
                        except json.JSONDecodeError:
                            # Already logged in process_message
                            pass
                    except asyncio.TimeoutError:
                        log(f"No more messages received after {3.0} seconds", "warning")
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        # Check if it's a normal closure
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
                    # Send keep-alive message
                    await asyncio.sleep(1)
                    log("Sending KeepAlive message...", "info", verbose)
                    await websocket.send(json.dumps({"type": "KeepAlive"}))
                    
                    # Wait briefly for any response to the keep-alive
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        await process_message(response, verbose)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        # No response or already closed, that's okay
                        pass
                
                    # Send close message
                    await asyncio.sleep(1)
                    log("Sending CloseStream message...", "important")
                    await websocket.send(json.dumps({"type": "CloseStream"}))
                    
                    # Wait for the server to close the connection gracefully
                    try:
                        # Try to receive a final message or wait for the connection to close
                        final_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        await process_message(final_response, verbose)
                    except websockets.exceptions.ConnectionClosed as e:
                        if e.code == 1000:
                            log("Server closed the connection normally after CloseStream", "important")
                        else:
                            log(f"Server closed the connection with code {e.code}", "warning")
                    except asyncio.TimeoutError:
                        log("No response after CloseStream, closing connection", "info")
            
            except Exception as e:
                # Check if this is a normal WebSocket closure
                if (isinstance(e, websockets.exceptions.ConnectionClosedOK) or
                    isinstance(e, websockets.exceptions.ConnectionClosedError) and 
                    hasattr(e, 'code') and e.code == 1000 or
                    "1000" in str(e) or
                    "received 1000 (OK)" in str(e)):
                    log("WebSocket connection closed normally", "info")
                else:
                    log(f"Error during WebSocket communication: {str(e)}", "error")
                    test_success = False
        
    except Exception as e:
        # Check if this is a normal WebSocket closure
        if (isinstance(e, websockets.exceptions.ConnectionClosedOK) or
            isinstance(e, websockets.exceptions.ConnectionClosedError) and 
            hasattr(e, 'code') and e.code == 1000 or
            "1000" in str(e) or
            "received 1000 (OK)" in str(e)):
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

async def process_message(message, verbose=False):
    """Process and log a message received from the WebSocket."""
    global test_success
    try:
        # Try to parse JSON
        data = json.loads(message)
        msg_type = data.get("type", "unknown")
        
        # Log based on message type
        if msg_type == "Welcome":
            session_id = data.get("session_id", "unknown")
            log(f"✅ Received Welcome message (Session ID: {session_id})", "success")
        elif msg_type == "SettingsApplied":
            log("✅ Received SettingsApplied message", "success")
        elif msg_type == "Error":
            error_message = data.get("message", "No error message")
            log(f"❌ Received Error message: {error_message}", "error")
            test_success = False
        elif msg_type == "KeepAliveResponse":
            log("ℹ️ Received KeepAliveResponse", "info", verbose)
        else:
            log(f"ℹ️ Received message type: {msg_type}", "info")
        
        # Print full message details if in verbose mode
        if verbose:
            log(f"Full message: {json.dumps(data, indent=2)}", "debug")
            
    except json.JSONDecodeError:
        log(f"❌ Could not parse response as JSON: {message}", "error")
        test_success = False

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
    parser = argparse.ArgumentParser(description="Advanced Voice Agent test for Gnosis")
    parser.add_argument("--hostname", default="ws://localhost:8080", 
                        help="Base WebSocket URL (default: ws://localhost:8080)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output with detailed message contents")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                        help="Maximum seconds to wait for responses (default: 5)")
    args = parser.parse_args()
    
    print(f"{Style.BRIGHT}{Fore.CYAN}Advanced Voice Agent Test{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Hostname:{Style.RESET_ALL} {args.hostname}")
    print(f"{Style.BRIGHT}Timeout:{Style.RESET_ALL} {args.timeout} seconds")
    print(f"{Style.BRIGHT}Verbose:{Style.RESET_ALL} {'Yes' if args.verbose else 'No'}")
    print("═════════════════════════════════════════")
    
    try:
        # Run the test
        asyncio.run(test_agent_proxy(args.hostname, args.verbose, args.timeout))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 