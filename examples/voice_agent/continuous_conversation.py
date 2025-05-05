#!/usr/bin/env python3
# continuous_conversation.py
# Example script that demonstrates continuous conversation with Deepgram Voice Agent
# using text-to-speech and completion helpers via the Gnosis proxy server

import os
import asyncio
import json
import tempfile
import websockets
import time
import argparse
import shutil
import datetime
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from tts_helper import DeepgramTTS
from completion_helper import OpenAICompletionHelper

# Load environment variables
load_dotenv()

# Configuration
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GNOSIS_URL = "ws://localhost:8080/v1/agent"  # Local Gnosis server
USER_TTS_MODEL = "aura-2-thalia-en"  # Voice model for generating user audio
AGENT_TTS_MODEL = (
    "aura-2-asteria-en"  # Voice model for agent responses (different from user)
)
LLM_MODEL = "gpt-4o-mini"  # Model for generating conversation continuations
CHUNK_SIZE = 4096  # Size of audio chunks to send
SILENCE_TIMEOUT = 5  # Number of seconds to wait before stopping continuous silence
MAX_TURNS = 3  # Default number of turns in the conversation


def create_slug(text, max_length=30):
    """Create a URL-friendly slug from text"""
    # Convert to lowercase and replace special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def create_conversation_folder(initial_message):
    """Create a unique folder for the conversation"""
    # Create a simple slug from the first few words
    words = initial_message.split()[:5]  # Use first 5 words max
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


async def main(
    initial_message: str = "Hello! How are you today?",
    chunk_size: int = CHUNK_SIZE,
    max_turns: int = MAX_TURNS,
    silence_timeout: int = SILENCE_TIMEOUT,
    user_tts_model: str = USER_TTS_MODEL,
    agent_tts_model: str = AGENT_TTS_MODEL,
):
    """
    Main function to run a continuous conversation with the Deepgram Voice Agent

    Args:
        initial_message: Message to start the conversation with
        chunk_size: Size of audio chunks to send
        max_turns: Number of conversation turns to complete
        silence_timeout: Number of seconds to wait after last event before stopping silence
        user_tts_model: Voice model to use for user messages
        agent_tts_model: Voice model to use for agent responses
    """
    # Initialize helpers
    tts = DeepgramTTS(api_key=DEEPGRAM_API_KEY)
    completion_helper = OpenAICompletionHelper(api_key=OPENAI_API_KEY, model=LLM_MODEL)

    # Create conversation folder
    conversation_dir = create_conversation_folder(initial_message)

    # Start with an initial message
    print(f"\n📢 [USER INITIAL]: {initial_message}")

    # Add initial message to conversation history
    completion_helper.add_message("user", initial_message)

    # Convert initial message to audio
    user_audio_path = conversation_dir / "1-user.wav"
    audio_data, _ = tts.generate_speech(
        text=initial_message,
        model=user_tts_model,
        encoding="linear16",  # Voice Agent expects linear16 (PCM)
        sample_rate=16000,  # Use 16kHz for compatibility
        container=None,  # Raw PCM
        output_file=str(user_audio_path),
    )
    print(f"✅ Saved initial user audio to {user_audio_path}")

    try:
        # Load audio bytes
        with open(user_audio_path, "rb") as f:
            audio_bytes = f.read()

        # Connect to Gnosis Voice Agent proxy
        print(f"🔄 Connecting to Gnosis Voice Agent proxy at {GNOSIS_URL}")

        # Set up headers if API key provided
        headers = {}
        if DEEPGRAM_API_KEY:
            headers["Authorization"] = f"Token {DEEPGRAM_API_KEY}"

        async with websockets.connect(
            GNOSIS_URL, additional_headers=headers
        ) as websocket:
            print("✅ Connected successfully to Gnosis")

            # Receive welcome message
            welcome = await websocket.recv()
            print(f"👋 Received welcome message")

            # Settings configuration
            print("🔄 Sending settings configuration...")
            settings = {
                "type": "SettingsConfiguration",
                "audio": {
                    "input": {"encoding": "linear16", "sample_rate": 16000},
                    "output": {
                        "encoding": "mp3",
                        "sample_rate": 24000,
                    },  # Request MP3 output
                },
                "agent": {
                    "listen": {"model": "nova-3"},
                    "think": {
                        "provider": {"type": "open_ai"},
                        "model": "gpt-4o-mini",
                        "instructions": "You are a helpful AI assistant. Keep responses concise.",
                    },
                    "speak": {"model": agent_tts_model},
                },
            }

            await websocket.send(json.dumps(settings))

            # Set up conversation tracking
            conversation = []
            conversation_turn = 0
            audio_turn_counter = 1  # Start at 1 for the first user message
            should_send_silence = True  # Flag to control silence sending
            silence_task = None  # Track the silence task
            last_event_time = time.time()  # Track time of last non-binary event

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
                    except:
                        pass

            # Process messages and maintain conversation
            async def process_conversation():
                nonlocal conversation_turn, audio_turn_counter, should_send_silence, last_event_time
                received_end_of_thought = False
                received_agent_response = False
                agent_response_text = ""
                agent_audio_data = bytearray()

                while conversation_turn < max_turns:
                    try:
                        response = await websocket.recv()

                        if isinstance(response, bytes):
                            # Accumulate audio response
                            agent_audio_data.extend(response)
                            print(f"🔊 Received audio chunk: {len(response)} bytes")
                        else:
                            last_event_time = (
                                time.time()
                            )  # Update last event time for non-binary messages

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
                                        agent_response_text = text
                                        received_agent_response = True
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
                                    print(f"🎵 Agent audio response complete")

                                    # Save the accumulated audio data
                                    if len(agent_audio_data) > 0:
                                        audio_turn_counter += 1
                                        agent_audio_path = (
                                            conversation_dir
                                            / f"{audio_turn_counter}-agent.mp3"
                                        )
                                        with open(agent_audio_path, "wb") as f:
                                            f.write(agent_audio_data)
                                        print(
                                            f"✅ Saved agent audio to {agent_audio_path} ({len(agent_audio_data)} bytes)"
                                        )

                                    # Generate next user message if we have an agent response
                                    if received_agent_response and agent_response_text:
                                        # Generate next user message
                                        user_response = (
                                            completion_helper.continue_conversation(
                                                agent_response_text
                                            )
                                        )
                                        print(
                                            f"\n🤔 [USER CONTINUATION]: {user_response}"
                                        )

                                        # Convert to speech
                                        audio_turn_counter += 1
                                        next_user_audio_path = (
                                            conversation_dir
                                            / f"{audio_turn_counter}-user.wav"
                                        )
                                        next_audio_data, _ = tts.generate_speech(
                                            text=user_response,
                                            model=user_tts_model,
                                            encoding="linear16",
                                            sample_rate=16000,
                                            container=None,
                                            output_file=str(next_user_audio_path),
                                        )
                                        print(
                                            f"✅ Saved user continuation audio to {next_user_audio_path}"
                                        )

                                        # Pause silence sending while we send user audio
                                        should_send_silence = False

                                        # Send the audio
                                        await send_audio_data(
                                            next_user_audio_path, chunk_size
                                        )

                                        # Resume silence sending
                                        should_send_silence = True

                                        # Reset for next turn
                                        conversation_turn += 1
                                        received_end_of_thought = False
                                        received_agent_response = False
                                        agent_response_text = ""
                                        agent_audio_data = bytearray()

                                        print(
                                            f"✅ Turn {conversation_turn}/{max_turns} complete"
                                        )

                                elif msg_type == "Error":
                                    error = data.get("message", "Unknown error")
                                    print(f"❌ Error: {error}")
                                    return

                            except json.JSONDecodeError:
                                print(f"⚠️ Received non-JSON string: {response[:100]}")

                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket connection closed")
                        return

                # Print conversation summary
                print("\n=== Conversation Summary ===")
                for i, msg in enumerate(conversation):
                    print(f"{msg['role']}: \"{msg['text']}\"")
                print("============================\n")

                print("✅ Continuous conversation complete")

            # Helper function to send audio data with rate limiting
            async def send_audio_data(audio_file_path, chunk_size):
                """Send audio data in chunks with rate limiting to simulate real-time speech"""
                # Load audio bytes
                with open(audio_file_path, "rb") as f:
                    audio_bytes = f.read()

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

            # Start conversation processor
            conversation_task = asyncio.create_task(process_conversation())

            # Start the silence task in the background
            silence_task = asyncio.create_task(send_continuous_silence())

            # Temporarily disable silence sending while we send the initial audio
            should_send_silence = False

            # Send initial audio
            await send_audio_data(user_audio_path, chunk_size)

            # Re-enable continuous silence sending
            should_send_silence = True
            print(
                "🔊 Started continuous silence transmission (open microphone simulation)"
            )

            # Wait for conversation to complete
            try:
                await conversation_task
            finally:
                # Stop the silence task
                should_send_silence = False
                if silence_task and not silence_task.done():
                    silence_task.cancel()
                    try:
                        await silence_task
                    except asyncio.CancelledError:
                        pass

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        print(f"🧹 Conversation saved in {conversation_dir}")

        # Display playback instructions
        print("\n=== How to Play Back the Conversation ===")
        print(f"cd {conversation_dir}")
        print("# To play user WAV files:")
        print("play *-user.wav")
        print("\n# To play agent MP3 files:")
        print("play *-agent.mp3")
        print("=======================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Continuous conversation with Voice Agent via Gnosis proxy"
    )
    parser.add_argument(
        "--message",
        default="Hello! How are you today?",
        help="Initial message to start the conversation",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=CHUNK_SIZE, help="Audio chunk size in bytes"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=MAX_TURNS,
        help="Number of conversation turns to complete",
    )
    parser.add_argument(
        "--silence-timeout",
        type=int,
        default=SILENCE_TIMEOUT,
        help="Seconds to wait after last event before stopping silence",
    )
    parser.add_argument(
        "--user-voice",
        default=USER_TTS_MODEL,
        help="TTS model to use for user messages",
    )
    parser.add_argument(
        "--agent-voice",
        default=AGENT_TTS_MODEL,
        help="TTS model to use for agent responses",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            initial_message=args.message,
            chunk_size=args.chunk_size,
            max_turns=args.turns,
            silence_timeout=args.silence_timeout,
            user_tts_model=args.user_voice,
            agent_tts_model=args.agent_voice,
        )
    )
