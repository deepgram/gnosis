#!/usr/bin/env python3
# basic.py
# Simple example of interacting with the Voice Agent API via local Gnosis server

import asyncio
import json
import websockets
import argparse
import os
import time
import datetime

from examples.helpers.tts_helper import DeepgramTTS
from examples.helpers.save_helper import (
    create_conversation_folder,
    save_conversation_log,
    save_audio_file,
    print_playback_instructions,
)
from examples.helpers.silence_helper import (
    send_continuous_silence,
    create_silence_frame,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Configuration
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GNOSIS_URL = "ws://localhost:8080/v1/agent/converse"  # Local Gnosis server
USER_TTS_MODEL = "aura-2-thalia-en"  # Voice model for generating user audio
AGENT_TTS_MODEL = "aura-2-andromeda-en"  # Voice model for agent responses
LLM_MODEL = "gpt-4o-mini"  # Model for generating conversation continuations
CHUNK_SIZE = 4096  # Size of audio chunks to send
SILENCE_TIMEOUT = 5  # Number of seconds to wait before stopping continuous silence
MAX_TURNS = 3  # Default number of turns in the conversation


async def main(
    text: str,
    system_prompt: str = "You are a helpful AI assistant. Keep responses concise.",
):
    """
    Basic interaction with the Voice Agent:
    1. Connect to the agent
    2. Send settings configuration
    3. Generate speech from text and send in chunks
    4. Process responses

    Args:
        text: Text to convert to speech and send to the agent
        chunk_size: Size of audio chunks to send
        silence_timeout: Seconds to wait after last event before stopping continuous silence
        system_prompt: System prompt to guide the agent's responses
    """
    # Create conversation folder
    conversation_dir = create_conversation_folder(text)

    # Initialize helpers
    tts = DeepgramTTS(api_key=DEEPGRAM_API_KEY)

    # Set up conversation tracking
    conversation = []

    # Generate audio from text
    print(f"📢 Converting text to speech: '{text}'")

    # Generate audio file directly in the conversation folder
    user_audio_path = conversation_dir / "1-user.wav"
    audio_data, _ = tts.generate_speech(
        text=text,
        model=USER_TTS_MODEL,
        encoding="linear16",  # Voice Agent expects linear16 (PCM)
        sample_rate=16000,  # Use 16kHz for compatibility
        container=None,  # Raw PCM
        output_file=str(user_audio_path),
    )
    print(f"✅ Generated and saved user audio to {user_audio_path}")

    # We no longer add the user message to conversation here
    # Let the ConversationText event handle it

    try:
        # Load audio bytes
        with open(user_audio_path, "rb") as f:
            audio_bytes = f.read()

        # Connect to WebSocket
        print(f"🔄 Connecting to local Gnosis Voice Agent at {GNOSIS_URL}")
        async with websockets.connect(GNOSIS_URL) as websocket:
            print("✅ Connected successfully")

            # Receive welcome message
            welcome = await websocket.recv()
            print(f"👋 Received welcome message")

            # Settings configuration with minimal required properties
            print("🔄 Sending settings configuration...")
            settings = {
                "type": "Settings",
                # Audio configuration - required for both input and output
                "audio": {
                    "input": {"encoding": "linear16", "sample_rate": 16000},
                    "output": {"encoding": "linear16", "sample_rate": 24000},
                },
                # Agent capabilities configuration
                "agent": {
                    # Listen capability (STT) - required
                    "listen": {"provider": {"model": "nova-3"}},
                    # Think capability (LLM) - required
                    "think": {
                        "provider": {
                            "model": LLM_MODEL,
                        },
                        "prompt": system_prompt,
                    },
                    # Speak capability (TTS) - required
                    "speak": {"provider": {"model": AGENT_TTS_MODEL}},
                },
            }

            await websocket.send(json.dumps(settings))

            # Track last event time for silence handling
            last_event_time = time.time()
            last_event_time_ref = [last_event_time]  # Mutable reference

            # Wait for settings to be applied
            settings_applied = False
            while not settings_applied:
                response = await websocket.recv()
                # Update last event time
                last_event_time = time.time()
                last_event_time_ref[0] = last_event_time

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
                silence_frame = create_silence_frame(100)  # 100ms of silence
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

            # Function to handle incoming messages
            async def process_messages():
                nonlocal conversation, last_event_time
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
                            last_event_time_ref[0] = last_event_time

                            try:
                                data = json.loads(response)
                                msg_type = data.get("type", "")

                                print(f"📨 Received message: {msg_type}")

                                if msg_type == "ConversationText":
                                    received_text = data.get("content", "")
                                    role = data.get("role", "")

                                    # Print based on role
                                    if role == "assistant":
                                        print(f'🤖 Agent: "{received_text}"')
                                    else:
                                        print(f'👤 Recognized: "{received_text}"')

                                    # Always add the message to conversation history
                                    # This ensures we log exactly what was recognized
                                    timestamp = datetime.datetime.now().strftime(
                                        "%H:%M:%S"
                                    )
                                    conversation.append(
                                        {
                                            "role": role,
                                            "content": received_text,
                                            "timestamp": timestamp,
                                        }
                                    )

                                    # Save conversation log incrementally
                                    save_conversation_log(
                                        conversation_dir, conversation
                                    )

                                elif msg_type == "UserStartedSpeaking":
                                    print("🎤 User started speaking")

                                elif msg_type == "AgentThinking":
                                    print("🤔 Agent is thinking...")

                                elif msg_type == "PromptUpdated":
                                    print("📝 Prompt was updated")

                                elif msg_type == "SpeakUpdated":
                                    print("🔊 Speak configuration was updated")

                                elif msg_type == "AgentAudioDone":
                                    print("🎵 Agent audio response complete")

                                    # Save the accumulated audio data
                                    if len(agent_audio_data) > 0:
                                        agent_audio_path = save_audio_file(
                                            conversation_dir=conversation_dir,
                                            audio_data=agent_audio_data,
                                            file_index=2,
                                            role="agent",
                                            extension="wav",
                                            sample_rate=24000,  # Match the output sample rate in settings
                                        )
                                        print(
                                            f"🔊 Saved agent audio on connection close to {agent_audio_path} ({len(agent_audio_data)} bytes)"
                                        )

                                    # We're done with basic interaction after getting one response
                                    return

                                elif msg_type == "Error":
                                    error_description = data.get("description", "")
                                    error_message = data.get(
                                        "message", ""
                                    )  # For legacy API
                                    error_code = data.get("code", "")

                                    error_details = (
                                        error_description
                                        or error_message
                                        or "Unknown error"
                                    )
                                    error_display = (
                                        f"{error_code}: {error_details}"
                                        if error_code
                                        else error_details
                                    )

                                    print(f"❌ Error: {error_display}")
                                    print(
                                        f"Full error details: {json.dumps(data, indent=2)}"
                                    )
                                    return

                                elif msg_type == "Warning":
                                    warning_description = data.get("description", "")
                                    warning_code = data.get("code", "")
                                    warning_display = (
                                        f"{warning_code}: {warning_description}"
                                        if warning_code
                                        else warning_description
                                    )
                                    print(f"⚠️ Warning: {warning_display}")

                            except json.JSONDecodeError:
                                print(f"⚠️ Received non-JSON string: {response[:100]}")
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed")

                    # Save any accumulated audio on connection close
                    if len(agent_audio_data) > 0:
                        agent_audio_path = save_audio_file(
                            conversation_dir=conversation_dir,
                            audio_data=agent_audio_data,
                            file_index=2,
                            role="agent",
                            extension="wav",
                            sample_rate=24000,  # Match the output sample rate in settings
                        )
                        print(
                            f"🔊 Saved agent audio on connection close to {agent_audio_path} ({len(agent_audio_data)} bytes)"
                        )
                    return

            # Start message processing in the background
            process_task = asyncio.create_task(process_messages())

            # Send audio data
            await send_audio_data(audio_bytes, CHUNK_SIZE)

            # Start continuous silence transmission
            silence_task = asyncio.create_task(
                send_continuous_silence(websocket, last_event_time_ref, SILENCE_TIMEOUT)
            )
            print(
                "🔊 Started continuous silence transmission (open microphone simulation)"
            )

            # Update the event time reference whenever we receive an event
            async def update_event_time():
                """Update the event time reference whenever a message is processed"""
                nonlocal last_event_time, last_event_time_ref
                while True:
                    await asyncio.sleep(0.1)  # Check every 100ms
                    if last_event_time > last_event_time_ref[0]:
                        last_event_time_ref[0] = last_event_time

            # Start time updater
            time_updater_task = asyncio.create_task(update_event_time())

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

                if time_updater_task and not time_updater_task.done():
                    time_updater_task.cancel()
                    try:
                        await time_updater_task
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
                    print(f"{msg['role']}: \"{msg['content']}\"")
                print("============================\n")

            print("✅ Voice agent interaction complete")

    finally:
        # Display playback instructions
        print(f"🧹 Conversation saved in {conversation_dir}")

        # Display playback instructions
        print_playback_instructions(conversation_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simple Voice Agent interaction with local Gnosis server"
    )
    parser.add_argument("--user", required=True, help="Text to send to the agent")
    parser.add_argument(
        "--system",
        default="You are a helpful AI assistant. Keep responses concise.",
        help="System prompt for the agent",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            text=args.user,
            system_prompt=args.system,
        )
    )
