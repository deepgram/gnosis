#!/usr/bin/env python3
# save_helper.py
# Helper module for creating conversation folders and saving conversation data
# Handles adding WAV headers to raw PCM audio data from Voice Agent API for proper playback

import re
import datetime
import inspect
import sys
import struct
from pathlib import Path
from typing import Dict, List, Any, Optional


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by removing punctuation and extra whitespace

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Remove punctuation and convert to lowercase
    text = re.sub(r"[^\w\s]", "", text.lower())
    # Replace multiple whitespace with a single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading and trailing whitespace
    return text.strip()


def get_project_root() -> Path:
    """
    Get the project root directory

    Returns:
        Path to the project root directory
    """
    # Starting from the current file
    current_file = Path(__file__).resolve()
    # Go up to examples/helpers, then examples, then the project root
    project_root = current_file.parent.parent.parent
    return project_root


def get_caller_script_name() -> str:
    """
    Get the name of the script that called the current function

    Returns:
        The name of the calling script without extension
    """
    # Get the current call stack
    stack = inspect.stack()

    # Start from index 1 to skip the current function
    # and go up the stack to find the first __main__ caller
    main_caller = None
    for frame in stack[1:]:
        module = inspect.getmodule(frame[0])
        if module:
            if module.__name__ == "__main__":
                main_caller = frame
                break

    # If we found a main caller, get its filename
    if main_caller:
        filename = Path(main_caller.filename).stem
        return filename

    # If we can't find a __main__ caller, try to get the parent module name
    for frame in stack[1:]:
        module = inspect.getmodule(frame[0])
        if module and module.__name__ != __name__:
            # Get just the last part of the module name (e.g., 'basic' from 'examples.voice_agent.basic')
            return module.__name__.split(".")[-1]

    # Fallback to the main script name in sys.argv[0]
    return Path(sys.argv[0]).stem


def create_slug(text: str, max_length: int = 30) -> str:
    """
    Create a URL-friendly slug from text

    Args:
        text: The text to convert to a slug
        max_length: Maximum length of the resulting slug

    Returns:
        A URL-friendly slug
    """
    # Convert to lowercase and replace special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def create_conversation_folder(text: str, base_dir: Optional[Path] = None) -> Path:
    """
    Create a unique folder for the conversation based on the input text

    Args:
        text: The text to use for folder name generation
        base_dir: Optional base directory path (defaults to /conversations at project root)

    Returns:
        Path to the created conversation directory
    """
    # Get the name of the calling script
    script_name = get_caller_script_name()

    # Create a simple slug from the first few words
    words = text.split()[:5]  # Use first 5 words max
    topic = " ".join(words)
    topic_slug = create_slug(topic)

    # Create folder with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # Prefix the folder name with the script name
    folder_name = f"{script_name}_{topic_slug}-{timestamp}"

    # Create conversations directory if it doesn't exist
    if base_dir is None:
        # Use the project root directory
        project_root = get_project_root()
        base_dir = project_root / "conversations"

    base_dir.mkdir(exist_ok=True)

    # Create conversation-specific directory
    conversation_dir = base_dir / folder_name
    conversation_dir.mkdir(exist_ok=True)

    print(f"📁 Created conversation folder: {conversation_dir}")
    return conversation_dir


def save_conversation_log(
    conversation_dir: Path,
    conversation: List[Dict[str, Any]],
    filename: str = "conversation.txt",
) -> Path:
    """
    Save the conversation to a text file

    Args:
        conversation_dir: Directory to save the conversation log
        conversation: List of conversation messages with role, text, and timestamp
        filename: Name of the log file

    Returns:
        Path to the saved log file
    """
    log_path = conversation_dir / filename

    with open(log_path, "w") as f:
        f.write("=== Conversation Log ===\n\n")
        for msg in conversation:
            timestamp = msg.get(
                "timestamp", datetime.datetime.now().strftime("%H:%M:%S")
            )
            role = msg.get("role", "unknown")
            # Try to get content first (new format), fall back to text (old format)
            content = msg.get("content", msg.get("text", ""))
            f.write(f"[{timestamp}] {role.upper()}: {content}\n\n")

    print(f"📝 Saved conversation log to {log_path}")
    return log_path


def create_wav_header(
    sample_rate: int = 24000,
    num_channels: int = 1,
    bits_per_sample: int = 16,
    data_length: int = 0,
) -> bytes:
    """
    Create a WAV header for PCM audio data

    Args:
        sample_rate: Sample rate in Hz (default: 24000)
        num_channels: Number of audio channels (default: 1 for mono)
        bits_per_sample: Bits per sample (default: 16 for linear16)
        data_length: Length of audio data in bytes

    Returns:
        WAV header as bytes
    """
    # RIFF header
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_length))  # File size - 8
    header.extend(b"WAVE")

    # FMT subchunk
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))  # Subchunk1Size (16 for PCM)
    header.extend(struct.pack("<H", 1))  # AudioFormat (1 for PCM)
    header.extend(struct.pack("<H", num_channels))  # NumChannels
    header.extend(struct.pack("<I", sample_rate))  # SampleRate

    bytes_per_sample = bits_per_sample // 8
    byte_rate = sample_rate * num_channels * bytes_per_sample
    block_align = num_channels * bytes_per_sample

    header.extend(struct.pack("<I", byte_rate))  # ByteRate
    header.extend(struct.pack("<H", block_align))  # BlockAlign
    header.extend(struct.pack("<H", bits_per_sample))  # BitsPerSample

    # Data subchunk
    header.extend(b"data")
    header.extend(struct.pack("<I", data_length))  # Subchunk2Size

    return bytes(header)


def save_audio_file(
    conversation_dir: Path,
    audio_data: bytes,
    file_index: int,
    role: str,
    extension: str = "wav",
    sample_rate: int = 24000,
) -> Path:
    """
    Save audio data to a file in the conversation directory.
    For WAV files, automatically adds proper WAV headers to raw PCM data.

    Args:
        conversation_dir: Directory to save the audio file
        audio_data: The audio data to save
        file_index: The index/order of the audio file
        role: The role of the speaker ("user" or "agent")
        extension: The file extension to use
        sample_rate: Sample rate in Hz (for WAV header if needed)

    Returns:
        Path to the saved audio file
    """
    audio_path = conversation_dir / f"{file_index}-{role}.{extension}"

    # If it's a WAV file, prepend WAV header for raw PCM data
    if extension.lower() == "wav" and not audio_data.startswith(b"RIFF"):
        # Add WAV header to raw PCM data
        wav_header = create_wav_header(
            sample_rate=sample_rate,
            num_channels=1,  # Mono audio
            bits_per_sample=16,  # 16-bit PCM
            data_length=len(audio_data),
        )
        with open(audio_path, "wb") as f:
            f.write(wav_header)
            f.write(audio_data)
        print(
            f"✅ Saved {role} audio to {audio_path} ({len(audio_data)} bytes + {len(wav_header)} byte header)"
        )
    else:
        # Save raw audio data as is
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        print(f"✅ Saved {role} audio to {audio_path} ({len(audio_data)} bytes)")

    return audio_path


def print_playback_instructions(conversation_dir: Path) -> None:
    """
    Print instructions for playing back the saved audio files

    Args:
        conversation_dir: Directory containing the conversation files
    """
    print("\n=== How to Play Back the Conversation ===")

    # Use absolute path for cd command
    print(f"cd {conversation_dir.absolute()}")

    print("# To play user WAV files:")
    print("play *-user.wav")
    print("\n# To play agent WAV files:")
    print("play *-agent.wav")
    print("=======================================\n")
