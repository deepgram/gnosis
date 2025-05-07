# Gnosis Example Helpers

This directory contains helper modules used across different examples in the Gnosis project.

## Available Helpers

### `save_helper.py`

Utility functions for saving conversation data and audio files:

- `create_slug()` - Create URL-friendly slugs from text
- `create_conversation_folder()` - Create a folder with a timestamp to store conversation data
- `save_conversation_log()` - Save conversation transcripts to a text file
- `save_audio_file()` - Save audio data with consistent naming
- `print_playback_instructions()` - Print instructions for playing back saved audio

### `tts_helper.py`

A helper class for converting text to speech using Deepgram's TTS API:

- `DeepgramTTS` - Class for generating speech from text
- `quick_tts()` - Simple function for quick text-to-speech conversion

### `completion_helper.py`

A helper class for generating conversation continuations with OpenAI:

- `OpenAICompletionHelper` - Class for generating conversational continuations
- `quick_completion()` - Simple function for quick text completions

## Usage

These helpers are designed to be imported and used across different examples:

```python
from examples.helpers.save_helper import create_conversation_folder, save_audio_file
from examples.helpers.tts_helper import DeepgramTTS
from examples.helpers.completion_helper import OpenAICompletionHelper
``` 