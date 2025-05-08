#!/usr/bin/env python3
# continuous.py
# Simple example of continuous conversation with the Voice Agent API via local Gnosis server
# Assumes the TTS and completion helpers are already configured

import os
import asyncio
import json
import websockets
import time
import argparse
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
from examples.helpers.completion_helper import OpenAICompletionHelper
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
    text: str = "Hello! How are you today?",
    max_turns: int = MAX_TURNS,
    system_prompt: str = "You are a helpful AI assistant. Keep responses concise.",
):
    """
    Main function to run a continuous conversation with the Deepgram Voice Agent

    Args:
        text: Text to convert to speech and send to the agent
        max_turns: Number of conversation turns to complete
        system_prompt: System prompt to guide the agent's responses
    """
    # Initialize helpers
    tts = DeepgramTTS(api_key=DEEPGRAM_API_KEY)
    completion_helper = OpenAICompletionHelper(api_key=OPENAI_API_KEY, model=LLM_MODEL)

    # Create conversation folder
    conversation_dir = create_conversation_folder(text)

    # Set up conversation tracking
    conversation = []
    conversation_turn = 0
    audio_turn_counter = 1  # Start at 1 for the first user message

    # Generate audio from text
    print(f"📢 Converting text to speech: '{text}'")

    # Add initial message to conversation history for the OpenAI completion helper
    # This is separate from our conversation log and only used for generating continuations
    completion_helper.add_message("user", text)

    # Convert initial message to audio
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

    # We don't add the user message to our conversation log here
    # Let the ConversationText event handle it

    try:
        # Load audio bytes
        with open(user_audio_path, "rb") as f:
            audio_bytes = f.read()

        # Connect to local Gnosis Voice Agent proxy
        print(f"🔄 Connecting to local Gnosis Voice Agent at {GNOSIS_URL}")

        async with websockets.connect(GNOSIS_URL) as websocket:
            print("✅ Connected successfully to Gnosis")

            # Receive welcome message
            welcome = await websocket.recv()
            print(f"👋 Received welcome message")

            # Settings configuration for V1 API
            print("🔄 Sending settings configuration...")
            settings = {
                "type": "Settings",
                "mip_opt_out": False,
                "experimental": False,
                "audio": {
                    "input": {"encoding": "linear16", "sample_rate": 16000},
                    "output": {
                        "encoding": "linear16",
                        "sample_rate": 24000,
                        "container": "none",
                    },
                },
                "agent": {
                    "language": "en",
                    "listen": {"provider": {"type": "deepgram", "model": "nova-3"}},
                    "think": {
                        "provider": {
                            "type": "open_ai",
                            "model": "gpt-4o-mini",
                            "temperature": 0.7,
                        },
                        "prompt": system_prompt,
                    },
                    "speak": {
                        "provider": {"type": "deepgram", "model": AGENT_TTS_MODEL}
                    },
                },
            }

            await websocket.send(json.dumps(settings))

            # Track time of last event (any message from server)
            last_event_time = time.time()
            # Mutable reference for the silence handler
            last_event_time_ref = [last_event_time]

            # Wait for settings to be applied
            settings_applied = False
            while not settings_applied:
                response = await websocket.recv()
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
                    except:
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

            # Function to handle incoming messages and maintain conversation
            async def process_messages():
                nonlocal conversation_turn, audio_turn_counter, last_event_time
                received_agent_response = False
                agent_response_text = ""
                agent_audio_data = bytearray()  # Accumulate agent audio
                # Track auto-generated messages to avoid duplication in completion_helper
                auto_generated_messages = []

                while conversation_turn < max_turns:
                    try:
                        response = await websocket.recv()

                        if isinstance(response, bytes):
                            # Accumulate audio response
                            agent_audio_data.extend(response)
                            print(f"🔊 Received audio chunk: {len(response)} bytes")
                            # Update last_event_time for binary messages (audio chunks) too
                            last_event_time = time.time()
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
                                        agent_response_text = received_text
                                        received_agent_response = True
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

                                elif msg_type == "AgentAudioDone":
                                    print(f"🎵 Agent audio response complete")

                                    # Save the accumulated audio data
                                    if len(agent_audio_data) > 0:
                                        audio_turn_counter += 1
                                        agent_audio_path = save_audio_file(
                                            conversation_dir=conversation_dir,
                                            audio_data=agent_audio_data,
                                            file_index=audio_turn_counter,
                                            role="agent",
                                            extension="wav",
                                            sample_rate=24000,  # Match the output sample rate in settings
                                        )
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

                                        # We'll let the ConversationText event handle it when it comes back
                                        # This ensures we only log what was actually recognized

                                        # Convert to speech
                                        audio_turn_counter += 1
                                        next_user_audio_path = (
                                            conversation_dir
                                            / f"{audio_turn_counter}-user.wav"
                                        )
                                        next_audio_data, _ = tts.generate_speech(
                                            text=user_response,
                                            model=USER_TTS_MODEL,
                                            encoding="linear16",
                                            sample_rate=16000,
                                            container=None,
                                            output_file=str(next_user_audio_path),
                                        )
                                        print(
                                            f"✅ Saved user continuation audio to {next_user_audio_path}"
                                        )

                                        # Send the audio
                                        with open(next_user_audio_path, "rb") as f:
                                            next_audio_bytes = f.read()
                                        await send_audio_data(
                                            next_audio_bytes, CHUNK_SIZE
                                        )

                                        # Reset for next turn
                                        conversation_turn += 1
                                        received_agent_response = False
                                        agent_response_text = ""
                                        agent_audio_data = bytearray()

                                        print(
                                            f"✅ Turn {conversation_turn}/{max_turns} complete"
                                        )

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

                            except json.JSONDecodeError:
                                print(f"⚠️ Received non-JSON string: {response[:100]}")

                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket connection closed")
                        return

                # Print conversation summary
                print("\n=== Conversation Summary ===")
                for i, msg in enumerate(conversation):
                    print(f"{msg['role']}: \"{msg['content']}\"")
                print("============================\n")

                print("✅ Continuous conversation complete")
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

            # Wait for the conversation to complete
            try:
                # Wait for processing to complete (happens when we reach max turns)
                await asyncio.wait_for(process_task, timeout=300)
            except asyncio.TimeoutError:
                print("⏱️ Timed out waiting for conversation to complete")
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

            print("✅ Continuous conversation complete")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        print(f"🧹 Conversation saved in {conversation_dir}")

        # Display playback instructions
        print_playback_instructions(conversation_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Continuous conversation with Voice Agent via local Gnosis proxy"
    )
    parser.add_argument(
        "--user",
        required=True,
        help="Text to send to the agent",
    )
    parser.add_argument(
        "--system",
        default="You are a helpful AI assistant. Keep responses concise.",
        help="System prompt for the agent",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=MAX_TURNS,
        help="Number of conversation turns to complete",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            text=args.user,
            max_turns=args.turns,
            system_prompt=args.system,
        )
    )
