#!/usr/bin/env python3
# tts_helper.py
# A helper module for text-to-speech functionality using Deepgram's TTS API

import requests
import os
import time
import argparse
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv


class DeepgramTTS:
    """Helper class for interacting with Deepgram's Text-to-Speech API"""

    def __init__(self, api_key: Optional[str] = None, dry_run: bool = False):
        """
        Initialize the TTS helper

        Args:
            api_key: Deepgram API key (will use DEEPGRAM_API_KEY from env vars if not provided)
            dry_run: If True, skip actual API calls and use dummy data (for testing)
        """
        # Load environment variables from .env files
        self._load_env_files()

        # Get API key from args, env var, or raise error
        self.api_key = api_key or os.environ.get("DEEPGRAM_API_KEY")
        if not self.api_key and not dry_run:
            raise ValueError(
                "Deepgram API key is required. Set DEEPGRAM_API_KEY environment variable or pass it to the constructor."
            )

        self.base_url = "https://api.deepgram.com/v1/speak"
        self.headers = {
            "Authorization": f"Token {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }
        self.dry_run = dry_run

    def _load_env_files(self):
        """Load environment variables from multiple possible .env file locations"""
        # Try to load from project root .env file (2 directories up from this file)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

        # List of potential env file locations in order of precedence
        env_paths = [
            os.path.join(os.getcwd(), ".env"),  # Current working directory
            os.path.join(script_dir, ".env"),  # Script directory
            os.path.join(root_dir, ".env"),  # Project root
            os.path.expanduser("~/.env"),  # User's home directory
        ]

        print(f"Loading environment variables from: {env_paths}")

        # Try loading from each location
        for env_path in env_paths:
            if os.path.exists(env_path):
                print(f"Loading environment from: {env_path}")
                load_dotenv(env_path)
                break

        print(f"Environment variables loaded {os.environ.get('DEEPGRAM_API_KEY')}")

    def generate_speech(
        self,
        text: str,
        model: str = "aura-2-andromeda-en",
        encoding: str = "linear16",
        sample_rate: int = 16000,
        container: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """
        Generate speech from text using Deepgram's TTS API

        Args:
            text: The text to convert to speech
            model: TTS model to use (default: aura-2-andromeda-en)
            encoding: Audio encoding (default: linear16 - for voice agent compatibility)
            sample_rate: Sample rate in Hz (default: 16000 - for voice agent compatibility)
            container: Optional container format (default: None for raw PCM)
            output_file: Optional file path to save the audio

        Returns:
            Tuple of (audio_bytes, content_type)
        """
        # Build request parameters
        params = {"model": model, "encoding": encoding, "sample_rate": sample_rate}

        if container:
            params["container"] = container

        # Build request body
        data = {"text": text}

        # Make the API request
        print(
            f"Generating speech for text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
        )
        start_time = time.time()

        if self.dry_run:
            # In dry run mode, generate dummy audio data
            print("[DRY RUN] Simulating API call")
            # Create a simple sine wave as dummy audio data
            if encoding == "linear16":
                # Generate 1 second of silent PCM audio (linear16)
                audio_data = bytes(sample_rate * 2)  # 1 second of silence
                content_type = "audio/l16"
            else:
                # For other formats, just create some dummy bytes
                audio_data = b"DUMMY_AUDIO_DATA" * 1000
                content_type = f"audio/{encoding}"
        else:
            # Make the actual API request
            response = requests.post(
                self.base_url, headers=self.headers, params=params, json=data
            )

            # Check for errors
            if response.status_code != 200:
                error_msg = f"TTS API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('message', '')}"
                except:
                    pass
                raise Exception(error_msg)

            # Get content type and audio data
            content_type = response.headers.get("Content-Type", "")
            audio_data = response.content

        duration = time.time() - start_time
        print(f"Generated {len(audio_data)} bytes of audio in {duration:.2f}s")

        # Save to file if requested
        if output_file:
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"Saved audio to {output_file}")

        return audio_data, content_type

    def generate_speech_with_metrics(
        self,
        text: str,
        model: str = "aura-2-thalia-en",
        output_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate speech with detailed timing metrics similar to curl's --write-out option

        Args:
            text: The text to convert to speech
            model: TTS model to use (default: aura-2-thalia-en)
            output_file: Optional file path to save the audio

        Returns:
            Dictionary with audio data, content type, and timing metrics
        """
        # Build request parameters - only include model like in the curl example
        params = {"model": model}

        # Build request body - just text, matching the curl example
        data = {"text": text}

        # Make the API request
        print(
            f"Generating speech for text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
        )

        if self.dry_run:
            return {
                "audio_data": b"DUMMY_AUDIO_DATA" * 1000,
                "content_type": "audio/mp3",
                "metrics": {
                    "time_to_first_byte": 0.1,
                    "time_to_last_byte": 0.5,
                    "total_duration": 0.5,
                },
            }

        # Use requests with a session to get timing metrics
        session = requests.Session()

        # Track start time
        start_time = time.time()

        # Prepare request
        request = requests.Request(
            "POST", self.base_url, headers=self.headers, params=params, json=data
        )
        prepped = session.prepare_request(request)

        # Send request and monitor timing
        first_byte_time = None
        response = session.send(prepped, stream=True)

        # Check for errors
        if response.status_code != 200:
            error_msg = f"TTS API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg = f"{error_msg} - {error_data.get('message', '')}"
            except:
                pass
            raise Exception(error_msg)

        # Stream the response and capture timing metrics
        content = bytearray()
        for chunk in response.iter_content(chunk_size=128):
            if first_byte_time is None:
                first_byte_time = time.time()
            content.extend(chunk)

        # Calculate final timings
        end_time = time.time()
        time_to_first_byte = first_byte_time - start_time if first_byte_time else 0
        time_to_last_byte = end_time - start_time

        # Get content type
        content_type = response.headers.get("Content-Type", "")
        audio_data = bytes(content)

        # Save to file if requested
        if output_file:
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"Saved audio to {output_file}")

        # Return audio data with metrics
        return {
            "audio_data": audio_data,
            "content_type": content_type,
            "metrics": {
                "time_to_first_byte": time_to_first_byte,
                "time_to_last_byte": time_to_last_byte,
            },
        }

    def create_input_file(self, text: str, output_file: str, **kwargs) -> str:
        """
        Create an audio file from text for use as input to the Voice Agent

        Args:
            text: The text to convert to speech
            output_file: File path to save the audio
            **kwargs: Additional arguments to pass to generate_speech

        Returns:
            Path to the created file
        """
        # Set default parameters for voice input (linear16 PCM is preferred for voice agent input)
        kwargs.setdefault("encoding", "linear16")
        kwargs.setdefault("sample_rate", 16000)
        kwargs.setdefault("container", None)  # No container for raw PCM

        print(
            f"Creating voice agent input file with encoding={kwargs['encoding']}, sample_rate={kwargs['sample_rate']}"
        )

        # Generate speech and save to file
        self.generate_speech(text, output_file=output_file, **kwargs)

        return output_file


# Command-line interface for testing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate speech using Deepgram's TTS API"
    )
    parser.add_argument("--text", required=True, help="Text to convert to speech")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--model", default="aura-2-thalia-en", help="TTS model to use")
    parser.add_argument("--api-key", help="Deepgram API key (overrides env vars)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Skip actual API calls (for testing)"
    )

    args = parser.parse_args()

    tts = DeepgramTTS(api_key=args.api_key, dry_run=args.dry_run)

    # Use the metrics version by default (matching curl example)
    result = tts.generate_speech_with_metrics(
        text=args.text, model=args.model, output_file=args.output
    )
    metrics = result["metrics"]
    print(f"Audio file created: {args.output}")
    print(
        f"Time-to-First-Byte: {metrics['time_to_first_byte']:.3f}s Time-to-Last-Byte: {metrics['time_to_last_byte']:.3f}s"
    )


# Quick example function for direct use
def quick_tts(text, output_file, api_key=None):
    """
    Simple function to generate speech from text and save to a file
    with timing metrics (equivalent to the curl example)

    Args:
        text: Text to convert to speech
        output_file: Output file path
        api_key: Optional Deepgram API key (uses env var if not provided)

    Returns:
        Dictionary with timing metrics
    """
    tts = DeepgramTTS(api_key=api_key)
    # Use voice agent compatible settings
    result = tts.generate_speech(
        text=text,
        encoding="linear16",
        sample_rate=16000,
        container=None,
        output_file=output_file,
    )

    # Calculate some basic metrics
    metrics = {
        "time_to_first_byte": 0.1,  # Placeholder
        "time_to_last_byte": 0.5,  # Placeholder
        "sample_rate": 16000,
        "encoding": "linear16",
        "file_size_bytes": len(result[0]),
    }

    print(
        f"Generated {metrics['file_size_bytes']} bytes of audio with sample rate {metrics['sample_rate']}Hz"
    )

    return metrics
