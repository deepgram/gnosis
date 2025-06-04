# Gnosis Examples

This directory contains examples demonstrating various capabilities of the Gnosis project.

## Running Examples

You can run the example scripts directly from the project root:

```bash
python -m examples.voice_agent.basic --user "Hello there!"
python -m examples.voice_agent.continuous --user "Hello, how are you today?" --turns 3
```

## Available Examples

### Voice Agent Examples

Examples demonstrating the use of Deepgram's Voice Agent API:

- `voice_agent/basic.py`: Simple example of a single-turn voice agent interaction
- `voice_agent/continuous.py`: Multi-turn conversation with the voice agent

Run with `--help` to see available options:

```bash
python examples/run.py voice_agent/basic --help
```

## Helper Modules

Common functionality is provided by helper modules in the `helpers/` directory:

- `tts_helper.py`: Text-to-speech functionality using Deepgram's TTS API
- `completion_helper.py`: Functions for generating conversation continuations with OpenAI
- `save_helper.py`: Utilities for saving conversation data and audio files

See the [helpers README](helpers/README.md) for more information.
