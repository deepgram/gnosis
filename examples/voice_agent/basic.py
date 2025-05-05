#!/usr/bin/env python3
# basic.py
# Simple example of interacting with the Voice Agent API

import asyncio
import json
import websockets
import argparse
import os
import time
import datetime
import re
from pathlib import Path
from typing import Optional

from tts_helper import DeepgramTTS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
GNOSIS_URL = "ws://localhost:8080/v1/agent"  # Local Gnosis server
DEFAULT_SERVER_URL = "wss://agent.deepgram.com/agent"  # Default server URL
TTS_MODEL = "aura-2-thalia-en"  # Voice model for generating audio
CHUNK_SIZE = 4096  # Size of audio chunks to send
SILENCE_TIMEOUT = 5  # Number of seconds to wait before stopping continuous silence


def create_slug(text, max_length=30):
    """Create a URL-friendly slug from text"""
    # Convert to lowercase and replace special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def create_conversation_folder(text):
    """Create a unique folder for the conversation"""
    # Create a simple slug from the first few words
    words = text.split()[:5]  # Use first 5 words max
    topic = " ".join(words)
    topic_slug = create_slug(topic)

    # Create folder with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
    folder_name = f"{topic_slug}-{timestamp}"

    # Create conversations directory if it doesn't exist
    base_dir = Path.cwd() / "conversations"
    base_dir.mkdir(exist_ok=True)

    # Create conversation-specific directory
    conversation_dir = base_dir / folder_name
    conversation_dir.mkdir(exist_ok=True)

    print(f"📁 Created conversation folder: {conversation_dir}")
    return conversation_dir


def save_conversation_log(conversation_dir, conversation):
    """Save the conversation to a text file"""
    log_path = conversation_dir / "conversation.txt"

    with open(log_path, "w") as f:
        f.write("=== Conversation Log ===\n\n")
        for msg in conversation:
            timestamp = msg.get(
                "timestamp", datetime.datetime.now().strftime("%H:%M:%S")
            )
            role = msg.get("role", "unknown")
            text = msg.get("text", "")
            f.write(f"[{timestamp}] {role.upper()}: {text}\n\n")

    print(f"📝 Saved conversation log to {log_path}")
    return log_path


async def basic_voice_interaction(
    server_url: str,
    text: str,
    chunk_size: int = CHUNK_SIZE,
    api_key: Optional[str] = None,
    model: str = TTS_MODEL,
    silence_timeout: int = SILENCE_TIMEOUT,
    dry_run: bool = False,
):
    """
    Basic interaction with the Voice Agent:
    1. Connect to the agent
    2. Send settings configuration
    3. Generate speech from text and send in chunks
    4. Process responses

    Args:
        server_url: WebSocket URL for the Voice Agent
        text: Text to convert to speech and send to the agent
        chunk_size: Size of audio chunks to send
        api_key: Deepgram API key (optional, uses env var if not provided)
        model: TTS model to use for speech generation
        silence_timeout: Seconds to wait after last event before stopping continuous silence
        dry_run: If True, skip actual API calls (for testing)
    """
    # Create conversation folder
    conversation_dir = create_conversation_folder(text)

    # Generate audio from text
    print(f"📢 Converting text to speech: '{text}'")

    # Generate audio file directly in the conversation folder
    user_audio_path = conversation_dir / "1-user.wav"

    # Generate audio with TTS
    tts = DeepgramTTS(api_key=api_key)
    audio_data, _ = tts.generate_speech(
        text=text,
        model=model,
        encoding="linear16",  # Voice Agent expects linear16 (PCM)
        sample_rate=16000,  # Use 16kHz for compatibility
        container=None,  # Raw PCM
        output_file=str(user_audio_path),
    )
    print(f"✅ Generated and saved user audio to {user_audio_path}")

    try:
        # Load audio bytes
        with open(user_audio_path, "rb") as f:
            audio_bytes = f.read()

        # Connect to WebSocket
        if dry_run:
            print(f"[DRY RUN] Would connect to {server_url}")
            return

        # Set up headers if API key provided
        headers = {}
        if api_key:
            headers["Authorization"] = f"Token {api_key}"

        print(f"🔄 Connecting to Voice Agent at {server_url}")
        async with websockets.connect(
            server_url, additional_headers=headers
        ) as websocket:
            print("✅ Connected successfully")
            
            # Receive welcome message
            await websocket.recv()
            
            # Settings configuration
            print("🔄 Sending settings configuration...")
            settings = {
                "type": "SettingsConfiguration",
                "audio": {
                    "input": {"encoding": "linear16", "sample_rate": 16000},
                    "output": {"encoding": "mp3", "sample_rate": 24000}
                },
                "agent": {
                    "listen": {"model": "nova-3"},
                    "think": {
                        "provider": {"type": "open_ai"},
                        "model": "gpt-4o-mini",
                        "instructions": "You are a helpful AI assistant. Keep responses concise."
                    },
                    "speak": {"model": model}
                }
            }
            
            await websocket.send(json.dumps(settings))
            
            # Wait for settings to be applied
            settings_applied = False
            while not settings_applied:
                response = await websocket.recv()
                if isinstance(response, str):
                    try:
                        data = json.loads(response)
                        if data.get("type") == "SettingsApplied":
                            settings_applied = True
                            print("✅ Settings applied, sending audio...")
                        elif data.get("type") == "Error":
                            error_msg = data.get("message", "Unknown error")
                            print(f"❌ Error: {error_msg}")
                            return
                    except Exception:
                        pass

            # Set up conversation tracking
            conversation = []
            last_event_time = time.time()  # Track time of last non-binary event
            should_send_silence = True  # Flag to control silence sending
            silence_task = None  # Track the silence task

            # Helper function to send audio data with rate limiting
            async def send_audio_data(audio_bytes, chunk_size):
                """Send audio data in chunks with rate limiting to simulate real-time speech"""
                # Send audio data (rate-limited to simulate real microphone)
                bytes_per_second = 32000  # 16kHz 16-bit PCM
                total_size = len(audio_bytes)
                chunks_sent = 0
                start_time = time.time()

                print(f"🎤 Sending audio: {total_size} bytes")

                # Send in chunks
                for i in range(0, total_size, chunk_size):
                    chunk = audio_bytes[i : i + chunk_size]
                    chunks_sent += 1

                    await websocket.send(chunk)

                    # Rate limit to simulate real-time audio
                    elapsed = time.time() - start_time
                    expected_time = (chunks_sent * chunk_size) / bytes_per_second
                    if elapsed < expected_time:
                        await asyncio.sleep(expected_time - elapsed)

                # Send silence frames to indicate end of speech
                silence_frame = b"\x00" * 3200  # 0.1s of silence at 16kHz 16-bit mono
                silence_frames_to_send = 10  # 1 second of silence

                print("🔊 Sending silence frames to indicate end of speech...")

                # Send silence frames with the same rate limiting
                for i in range(silence_frames_to_send):
                    chunks_sent += 1
                    await websocket.send(silence_frame)

                    # Rate limit consistently with previous audio
                    elapsed = time.time() - start_time
                    expected_time = (chunks_sent * 3200) / bytes_per_second
                    if elapsed < expected_time:
                        await asyncio.sleep(expected_time - elapsed)

                print(
                    f"✅ Audio sent: {total_size} bytes + {silence_frames_to_send} silence frames"
                )
                return

            # Create a task to receive messages
            async def process_messages():
                nonlocal conversation, last_event_time
                received_end_of_thought = False
                agent_audio_data = bytearray()  # Accumulate agent audio

                try:
                    while True:
                        response = await websocket.recv()

                        if isinstance(response, bytes):
                            # Accumulate audio response
                            agent_audio_data.extend(response)
                            print(f"🔊 Received audio chunk: {len(response)} bytes")
                        else:
                            # Update last event time for non-binary messages
                            last_event_time = time.time()

                            try:
                                data = json.loads(response)
                                msg_type = data.get("type", "")

                                print(f"📨 Received message: {msg_type}")

                                if msg_type == "ConversationText":
                                    text = data.get("text", "") or data.get(
                                        "content", ""
                                    )

                                    # Determine role
                                    if received_end_of_thought:
                                        role = "assistant"
                                        print(f'🤖 Agent: "{text}"')
                                    else:
                                        role = "user"
                                        print(f'👤 Recognized: "{text}"')

                                    # Add to conversation history
                                    timestamp = datetime.datetime.now().strftime(
                                        "%H:%M:%S"
                                    )
                                    conversation.append(
                                        {
                                            "role": role,
                                            "text": text,
                                            "timestamp": timestamp,
                                        }
                                    )

                                    # Save conversation log incrementally
                                    save_conversation_log(
                                        conversation_dir, conversation
                                    )

                                elif msg_type == "EndOfThought":
                                    received_end_of_thought = True
                                    print("✓ Agent has processed request")

                                elif msg_type in ["AgentAudioDone", "SpeechFinished"]:
                                    print("🎵 Agent audio response complete")
                                    
                                    # Save the accumulated audio data
                                    if len(agent_audio_data) > 0:
                                        agent_audio_path = conversation_dir / "2-agent.mp3"
                                        with open(agent_audio_path, "wb") as f:
                                            f.write(agent_audio_data)
                                        print(f"✅ Saved agent audio to {agent_audio_path} ({len(agent_audio_data)} bytes)")
                                    
                                    # We're done with basic interaction after getting one response
                                    return
                                
                                elif msg_type == "Error":
                                    error = data.get("message", "Unknown error")
                                    print(f"❌ Error: {error}")
                                    return

                            except json.JSONDecodeError:
                                print(f"⚠️ Received non-JSON string: {response[:100]}")
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed")

                    # Save any accumulated audio on connection close
                    if len(agent_audio_data) > 0:
                        agent_audio_path = conversation_dir / "2-agent.mp3"
                        with open(agent_audio_path, "wb") as f:
                            f.write(agent_audio_data)
                        print(
                            f"🔊 Saved agent audio on connection close to {agent_audio_path} ({len(agent_audio_data)} bytes)"
                        )
                    return

            # Task to continuously send silence when not sending actual audio
            async def send_continuous_silence():
                nonlocal should_send_silence, last_event_time
                silence_frame = b"\x00" * 3200  # 0.1s of silence at 16kHz 16-bit mono
                silence_count = 0

                try:
                    while True:
                        # Check if we should stop silence based on timeout
                        current_time = time.time()
                        if current_time - last_event_time > silence_timeout:
                            print(
                                f"⏱️ Silence timeout reached ({silence_timeout}s since last event), stopping continuous silence"
                            )
                            return

                        # Only send silence if explicitly enabled
                        if should_send_silence:
                            await websocket.send(silence_frame)
                            silence_count += 1

                            # Log every 30 frames (3 seconds)
                            if silence_count % 30 == 0:
                                print(f"🔊 Sent {silence_count} silence frames so far")

                            # Sleep to simulate real microphone rate (0.1s per frame)
                            await asyncio.sleep(0.1)
                        else:
                            # When paused, wait a bit before checking again
                            await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"⚠️ Silence task error: {e}")

            # Start message processing in the background
            process_task = asyncio.create_task(process_messages())

            # Temporarily disable silence sending while we send initial audio
            should_send_silence = False

            # Send audio data
            await send_audio_data(audio_bytes, chunk_size)

            # Start continuous silence transmission
            should_send_silence = True
            silence_task = asyncio.create_task(send_continuous_silence())
            print(
                "🔊 Started continuous silence transmission (open microphone simulation)"
            )

            # Wait for the response or timeout
            try:
                # Wait for processing to complete (happens when we get a response)
                await asyncio.wait_for(process_task, timeout=30)
            except asyncio.TimeoutError:
                print("⏱️ Timed out waiting for agent response")
            finally:
                # Clean up tasks
                if silence_task and not silence_task.done():
                    silence_task.cancel()
                    try:
                        await silence_task
                    except asyncio.CancelledError:
                        pass

                if process_task and not process_task.done():
                    process_task.cancel()
                    try:
                        await process_task
                    except asyncio.CancelledError:
                        pass

            # Print conversation summary
            if conversation:
                print("\n=== Conversation Summary ===")
                for i, msg in enumerate(conversation):
                    print(f"{msg['role']}: \"{msg['text']}\"")
                print("============================\n")

            print("✅ Voice agent interaction complete")

    finally:
        # Display playback instructions
        print(f"🧹 Conversation saved in {conversation_dir}")
        
        # Display instructions for playing back files
        print("\n=== How to Play Back the Conversation ===")
        print(f"cd {conversation_dir}")
        print("# To play user WAV files:")
        print("play *-user.wav")
        print("\n# To play agent MP3 files:")
        print("play *-agent.mp3")
        print("=======================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simple Voice Agent interaction example"
    )
    parser.add_argument(
        "--server", default=DEFAULT_SERVER_URL, help="WebSocket server URL"
    )
    parser.add_argument("--text", required=True, help="Text to send to the agent")
    parser.add_argument(
        "--chunk-size", type=int, default=CHUNK_SIZE, help="Audio chunk size in bytes"
    )
    parser.add_argument("--api-key", help="Deepgram API key (defaults to env var)")
    parser.add_argument("--model", default=TTS_MODEL, help="TTS model to use")
    parser.add_argument(
        "--silence-timeout",
        type=int,
        default=SILENCE_TIMEOUT,
        help="Seconds to wait after last event before stopping silence",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip actual API calls")
    parser.add_argument(
        "--use-gnosis", action="store_true", help="Use local Gnosis server"
    )

    args = parser.parse_args()

    # If using Gnosis, use localhost
    if args.use_gnosis:
        server_url = GNOSIS_URL
    else:
        server_url = args.server

    asyncio.run(
        basic_voice_interaction(
            server_url=server_url,
            text=args.text,
            chunk_size=args.chunk_size,
            api_key=args.api_key,
            model=args.model,
            silence_timeout=args.silence_timeout,
            dry_run=args.dry_run,
        )
    )
