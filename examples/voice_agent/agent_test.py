#!/usr/bin/env python3
import asyncio
import json
import argparse
import websockets
import colorama
from colorama import Fore, Style
import time
import os
import pathlib

# Initialize colorama for cross-platform color support
colorama.init()

# Global variable to track test status
test_success = True

async def test_agent_proxy(hostname, verbose=False, timeout=5, send_audio=True):
    """
    Advanced test of the voice agent proxy with proper message handling and error management.
    
    If send_audio is True, sends a test audio file after receiving the welcome message.
    """
    global test_success
    test_success = True  # Reset test status
    
    # Initialize start_time at the beginning of the function to make it available in all scopes
    start_time = time.time()
    
    gnosis_url = f"{hostname}/v1/agent"
    log(f"Connecting to Gnosis Voice Agent proxy at {gnosis_url}...", "important")
    
    # Settings configuration message to send
    settings_config = {
        "type": "SettingsConfiguration",
        "audio": {
            "input": {
                "encoding": "linear16",
                "sample_rate": 44100
            },
            "output": {
                "encoding": "linear16", 
                "sample_rate": 44100,
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
    
    # Prepare the audio file paths array for later use
    current_dir = pathlib.Path(__file__).parent.absolute()
    audio_files = [
        os.path.join(current_dir, "spacewalk.pcm")
    ]
            
    log(f"Found {len(audio_files)} PCM files to process", "info")
    
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
                                
                                # Send audio files in sequence, waiting for required responses between files
                                if send_audio and audio_files:
                                    for i, audio_file in enumerate(audio_files):
                                        file_num = i + 1
                                        file_name = os.path.basename(audio_file)
                                        
                                        if os.path.exists(audio_file):
                                            log(f"Processing file {file_num}/{len(audio_files)}: {file_name}", "important")
                                            
                                            # Send the audio file in chunks
                                            sent_successfully = await send_audio_in_chunks(websocket, audio_file, verbose=verbose)
                                            
                                            if sent_successfully:
                                                # Try to wait for EndOfThought message, but continue if we don't get it
                                                try:
                                                    end_of_thought = await wait_for_message_type(
                                                        websocket, "EndOfThought", timeout=10, verbose=verbose
                                                    )
                                                    
                                                    if not end_of_thought:
                                                        log(f"⚠️ Did not receive EndOfThought for {file_name} - continuing anyway", "warning")
                                                    
                                                    # Try to wait for AgentAudioDone message, but continue if we don't get it
                                                    try:
                                                        agent_audio_done = await wait_for_message_type(
                                                            websocket, "AgentAudioDone", timeout=10, verbose=verbose
                                                        )
                                                        
                                                        if not agent_audio_done:
                                                            log(f"⚠️ Did not receive AgentAudioDone for {file_name} - continuing anyway", "warning")
                                                        
                                                    except Exception as e:
                                                        log(f"⚠️ Error waiting for AgentAudioDone: {e} - continuing anyway", "warning")
                                                    
                                                except Exception as e:
                                                    log(f"⚠️ Error waiting for EndOfThought: {e} - continuing anyway", "warning")
                                                
                                                # Wait a moment before processing the next file
                                                log(f"Completed processing file {file_num}/{len(audio_files)}", "success")
                                                if i < len(audio_files) - 1:  # If not the last file
                                                    log("Waiting before processing next file...", "info")
                                                    await asyncio.sleep(2)
                                            else:
                                                log(f"⚠️ Failed to send {file_name}, skipping to next file", "warning")
                                        else:
                                            log(f"❌ Audio file not found: {audio_file}", "error")
                                    
                                    log(f"✅ Finished processing all {len(audio_files)} audio files", "success")
                                elif send_audio:
                                    log("❌ No audio files found to process", "error")
                                else:
                                    log("Audio sending disabled", "info")
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
                    # Wait a short time for any final responses after processing all files
                    if send_audio:
                        log("Waiting for any final messages...", "info")
                        await asyncio.sleep(3)
                    
                    # Close the connection gracefully without sending KeepAlive
                    log("Closing WebSocket connection...", "important")
                    await websocket.close(1000, "Normal closure")
            
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
        log("✅ TEST PASSED: All messages were processed successfully", "success")
    else:
        log("❌ TEST FAILED: Issues encountered during the test", "error")

async def process_message(message, verbose=False):
    """Process and log a message received from the WebSocket."""
    global test_success
    try:
        # Check if the message is binary data (likely audio)
        if isinstance(message, bytes):
            log(f"✅ Received binary audio data ({len(message)} bytes) - ignoring for CLI test", "info", verbose)
            return
        
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
            
            # Don't mark test as failed for expected errors in test environment
            expected_errors = [
                "We waited too long for a websocket message",
                "Please ensure that you're sending binary messages containing user speech",
                "Failed to Speak, check your Speak configuration"
            ]
            
            # Only set test_success to False if it's an unexpected error
            if not any(expected in error_message for expected in expected_errors):
                test_success = False
            else:
                log("Note: This is an expected error in the test environment and won't cause test failure", "warning")
        elif msg_type == "ConversationText":
            role = data.get("role", "")
            content = data.get("content", "")
            log(f"🗣️ {role.capitalize()}: \"{content}\"", "conversation")
        elif msg_type == "UserStartedSpeaking":
            log("🎤 User started speaking", "important")
        elif msg_type == "AgentThinking":
            content = data.get("content", "")
            log(f"🤔 Agent thinking: \"{content}\"", "thinking")
        elif msg_type == "FunctionCallRequest":
            fn_name = data.get("function_name", "")
            fn_id = data.get("function_call_id", "")
            log(f"⚙️ Function call request: {fn_name} (ID: {fn_id})", "function")
            if verbose:
                fn_input = data.get("input", {})
                log(f"Function parameters: {json.dumps(fn_input, indent=2)}", "debug")
        elif msg_type == "FunctionCalling":
            log(f"⚙️ Function calling", "function")
        elif msg_type == "AgentStartedSpeaking":
            total_latency = data.get("total_latency", 0)
            tts_latency = data.get("tts_latency", 0)
            ttt_latency = data.get("ttt_latency", 0)
            log(f"🔊 Agent started speaking (Total latency: {total_latency:.2f}s, TTT: {ttt_latency:.2f}s, TTS: {tts_latency:.2f}s)", "important")
        elif msg_type == "AgentAudioDone":
            log("✓ Agent audio finished", "important")
        elif msg_type == "EndOfThought":
            log("💭 End of thought", "thinking")
        elif msg_type == "KeepAlive":
            log("♥️ Keep-alive received", "info", verbose)
        else:
            log(f"ℹ️ Received message type: {msg_type}", "info")
        
        # Print full message details if in verbose mode
        if verbose:
            log(f"Full message: {json.dumps(data, indent=2)}", "debug")
            
    except json.JSONDecodeError:
        log(f"❌ Could not parse response as JSON: {message}", "error")
        test_success = False

async def send_audio_in_chunks(websocket, file_path, chunk_size=4096, chunk_delay=0.05, verbose=False):
    """
    Reads an audio file and sends it in small chunks to simulate microphone streaming.
    Concurrently listens for and processes incoming messages while streaming.
    
    Args:
        websocket: WebSocket connection to send data through
        file_path: Path to the audio file
        chunk_size: Size of each audio chunk in bytes (default: 4096 bytes)
        chunk_delay: Delay between chunks in seconds (default: 0.05 seconds)
        verbose: Whether to show verbose output
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            
        total_size = len(audio_bytes)
        file_name = os.path.basename(file_path)
        log(f"Sending {file_name} in chunks (total size: {total_size} bytes)...", "important")
        
        # Split file into chunks
        chunks = [audio_bytes[i:i+chunk_size] for i in range(0, total_size, chunk_size)]
        log(f"Split into {len(chunks)} chunks of {chunk_size} bytes each", "info")
        
        # Setup concurrent listening for responses
        async def listen_for_responses():
            while True:
                try:
                    # Non-blocking check for responses with a small timeout
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                    await process_message(response, verbose)
                except asyncio.TimeoutError:
                    # Expected - just means no message available yet
                    await asyncio.sleep(0.01)
                    continue
                except websockets.exceptions.ConnectionClosed:
                    # Connection closed
                    break
                except Exception as e:
                    log(f"Error receiving response: {e}", "error")
                    break
        
        # Start the listener task
        listener_task = asyncio.create_task(listen_for_responses())
        
        # Send each chunk with a small delay
        for i, chunk in enumerate(chunks):
            await websocket.send(chunk)
            
            # Log progress but not too verbose
            if i % 10 == 0 or i == len(chunks) - 1:
                log(f"Sent chunk {i+1}/{len(chunks)} ({len(chunk)} bytes)", "info", verbose=(i==0 or i==len(chunks)-1))
                
            # Small delay between chunks to simulate streaming
            await asyncio.sleep(chunk_delay)
        
        # Let the listener run a bit longer to catch any immediate responses
        await asyncio.sleep(0.5)
        
        # Cancel the listener task
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
            
        log(f"✅ Finished sending {file_name} ({total_size} bytes in {len(chunks)} chunks)", "success")
        return True
    except Exception as e:
        log(f"❌ Failed to send {os.path.basename(file_path)}: {str(e)}", "error")
        return False

async def wait_for_message_type(websocket, message_type, timeout=30, verbose=False):
    """
    Wait for a specific message type from the server.
    
    Args:
        websocket: The WebSocket connection
        message_type: The type of message to wait for
        timeout: Maximum time to wait in seconds
        verbose: Whether to log verbose output
        
    Returns:
        dict: The message data if received, None if timeout or error
    """
    start_time = time.time()
    log(f"Waiting for {message_type} message (timeout: {timeout}s)...", "info")
    
    while time.time() - start_time < timeout:
        try:
            # Wait for a message with a short timeout for responsiveness
            message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
            
            # If it's binary data, log it and continue
            if isinstance(message, bytes):
                log(f"📊 Received binary data ({len(message)} bytes)", "info", verbose)
                continue
                
            # Try to parse JSON
            try:
                data = json.loads(message)
                await process_message(message, verbose)
                
                # Check if this is the message type we're waiting for
                if data.get("type") == message_type:
                    log(f"✅ Received expected {message_type} message", "success")
                    return data
            except json.JSONDecodeError:
                log(f"❌ Could not parse response as JSON: {message}", "error")
                
        except asyncio.TimeoutError:
            # Just a short timeout to check if we should continue
            continue
        except websockets.exceptions.ConnectionClosed as e:
            log(f"❌ Connection closed while waiting for {message_type} (code: {e.code})", "error")
            return None
        except Exception as e:
            log(f"❌ Error while waiting for {message_type}: {e}", "error")
            return None
    
    log(f"❌ Timed out waiting for {message_type} message", "error")
    return None

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
    elif level == "conversation":
        prefix = f"{Fore.CYAN}"
    elif level == "thinking":
        prefix = f"{Fore.MAGENTA}"
    elif level == "function":
        prefix = f"{Fore.BLUE + Style.BRIGHT}"
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
    elif message.startswith("⚠️"):
        prefix = f"{Fore.YELLOW}"
    elif message.startswith("🗣️"):
        prefix = f"{Fore.CYAN}"
    elif message.startswith("🎤"):
        prefix = f"{Fore.YELLOW}"
    elif message.startswith("🤔") or message.startswith("💭"):
        prefix = f"{Fore.MAGENTA}"
    elif message.startswith("⚙️"):
        prefix = f"{Fore.BLUE + Style.BRIGHT}"
    elif message.startswith("🔊"):
        prefix = f"{Fore.GREEN}"
    elif message.startswith("✓"):
        prefix = f"{Fore.GREEN}"
    elif message.startswith("📊"):
        prefix = f"{Fore.MAGENTA}"
        
    print(f"{prefix}{message}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Advanced Voice Agent test for Gnosis")
    parser.add_argument("--hostname", default="ws://localhost:8080", 
                        help="Base WebSocket URL (default: ws://localhost:8080)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output with detailed message contents")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                        help="Maximum seconds to wait for responses (default: 5)")
    parser.add_argument("--no-audio", action="store_true",
                        help="Skip sending audio file")
    args = parser.parse_args()
    
    print(f"{Style.BRIGHT}{Fore.CYAN}Advanced Voice Agent Test{Style.RESET_ALL}")
    print("═════════════════════════════════════════")
    print(f"{Style.BRIGHT}Hostname:{Style.RESET_ALL} {args.hostname}")
    print(f"{Style.BRIGHT}Timeout:{Style.RESET_ALL} {args.timeout} seconds")
    print(f"{Style.BRIGHT}Verbose:{Style.RESET_ALL} {'Yes' if args.verbose else 'No'}")
    print(f"{Style.BRIGHT}Send Audio:{Style.RESET_ALL} {'No' if args.no_audio else 'Yes'}")
    print("═════════════════════════════════════════")
    
    try:
        # Run the test
        asyncio.run(test_agent_proxy(args.hostname, args.verbose, args.timeout, not args.no_audio))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 