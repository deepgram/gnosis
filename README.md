# Gnosis

_(ˈnəʊ.sɪs)_  
_noun_

1. Knowledge of spiritual mysteries.
   - _Example:_ "The philosopher dedicated his life to the pursuit of gnosis."

**Origin:**  
Late 16th century: from Greek _gnōsis_, meaning 'knowledge', from _gignōskein_, meaning 'to know'.

---

Gnosis is an intelligence API service, and an API proxy for OpenAI Chat Completions and Deepgram Voice Agent.

## Overview

Gnosis works as a proxy to the OpenAI Chat Completion's API and the Deepgram Voice Agent API. It provides enhanced context about Deepgram features to these services.

## TODOs

Check out the [to-do](TODO.md) list for outstanding tasks that have been ideated.

## Features

- **OpenAI API Proxy**: Forwards requests to OpenAI's Chat Completions API
  - Endpoint: `POST /v1/chat/completions`
  - Target: `https://api.openai.com/v1/chat/completions`

- **Deepgram WebSocket Proxy**: Forwards WebSocket connections to Deepgram Voice Agent
  - Endpoint: `WSS /v1/agent`
  - Target: `wss://agent.deepgram.com/v1/agent`

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## API Endpoints

### OpenAI Proxy

- `POST /v1/chat/completions` - Proxy for OpenAI's chat completions API

Example:

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "How can I transcribe a file with Deepgram?"}]}'
```

### Deepgram Proxy

- `WebSocket /v1/agent` - WebSocket proxy for Deepgram's voice agent API

## Development

To run in development mode with auto-reload:

```bash
python run.py
```

The application will use hot reloading in development mode.

### Local Setup

1. Clone this repository

2. Run the developer environment setup script:

   ```bash
   ./.bin/setup.sh
   ```

   This script will:
   - Create a virtual environment
   - Install dependencies
   - Create a default `.env` file if one doesn't exist
   - Install Git hooks for consistent commit message formatting

3. Update your `.env` file with your actual API keys for OpenAI and Deepgram

## License

For license details, see the [LICENSE](LICENSE) file.
