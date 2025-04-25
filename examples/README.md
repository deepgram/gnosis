# Gnosis API Examples

This directory contains example scripts for interacting with the Gnosis API.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Chat Completion Examples

### Basic Chat Completion

Simple example to send a chat completion request:

```bash
python chat_completions/basic.py --user "Tell me a joke about programming"
```

Options:
- `--host`: API host (default: http://localhost:8080)
- `--model`: Model to use (default: gpt-4o-mini)
- `--system`: System message
- `--user`: User message
- `--temperature`: Temperature (0.0-1.0)
- `--max-tokens`: Maximum tokens
- `--stream`: Enable streaming
- `--verbose`: Show detailed output

### Streamed Chat Completion

Example showing streaming response with real-time output:

```bash
python chat_completions/stream_response.py --question "Explain quantum computing"
```

Options:
- `--host`: API host
- `--model`: Model to use
- `--question`: Question to ask
- `--system-message`: System message
- `--debug`: Show debug info

### Function Calling Example

Demonstrates the OpenAI function calling capability:

```bash
python chat_completions/function_call.py --debug
```

Options:
- `--host`: API host
- `--model`: Model to use
- `--stream`: Enable streaming
- `--debug`: Show debug info
- `--verbose`: Show verbose output

## Voice Agent Examples

### Basic Voice Agent Test

Simple test for the Deepgram Voice Agent proxy:

```bash
python voice_agent/basic.py
```

Options:
- `--hostname`: WebSocket URL (default: ws://localhost:8080)
- `--verbose`: Show detailed logs

### Advanced Voice Agent Test

More advanced WebSocket test with better error handling:

```bash
python voice_agent/agent_test.py --debug
```

Options:
- `--hostname`: WebSocket URL
- `--debug`: Show debug info 