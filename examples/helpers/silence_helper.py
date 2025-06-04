#!/usr/bin/env python3
# silence_helper.py
# Helper module for handling silence in voice agent conversations

import asyncio
import time


async def send_continuous_silence(websocket, last_event_time_ref, silence_timeout=5):
    """
    Send continuous silence to keep the connection alive until timeout after last event.
    The function tracks the last event time using a mutable reference (list) which can
    be updated externally when events are received.

    Args:
        websocket: The websocket connection to send silence to
        last_event_time_ref: A mutable object (list) containing the timestamp of the last event
        silence_timeout: Number of seconds to wait after last event before stopping

    Returns:
        None when the silence timeout is reached
    """
    silence_frame = create_silence_frame(100)  # 100ms of silence (0.1s)
    silence_count = 0

    try:
        while True:
            # Check if we should stop silence based on timeout
            current_time = time.time()
            if current_time - last_event_time_ref[0] > silence_timeout:
                print(
                    f"⏱️ Silence timeout reached ({silence_timeout}s since last event), stopping continuous silence"
                )
                return

            # Send silence frame
            await websocket.send(silence_frame)
            silence_count += 1

            # Log every 30 frames (3 seconds)
            if silence_count % 30 == 0:
                print(f"🔊 Sent {silence_count} silence frames so far")

            # Sleep to simulate real microphone rate (0.1s per frame)
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"⚠️ Silence task error: {e}")


def create_silence_frame(duration_ms=100, sample_rate=16000):
    """
    Create a frame of silence for the specified duration

    Args:
        duration_ms: Duration of silence in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        Bytes object containing the silence frame
    """
    # Calculate number of bytes needed for silence frame
    # 2 bytes per sample (16-bit PCM)
    num_bytes = (duration_ms / 1000) * sample_rate * 2
    # Create and return the silence frame
    return b"\x00" * int(num_bytes)
