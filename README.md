# Gnosis

An intelligence API proxy for OpenAI Chat Completions and Deepgram Voice Agent.

## Overview

Gnosis works as a proxy to the OpenAI Chat Completion's API and the Deepgram Voice Agent API. It provides a simple and clean way to route requests to these services.

## Features

- **OpenAI API Proxy**: Forwards requests to OpenAI's Chat Completions API
  - Endpoint: `POST /v1/chat/completions`
  - Target: `https://api.openai.com/v1/chat/completions`

- **Deepgram WebSocket Proxy**: Forwards WebSocket connections to Deepgram Voice Agent
  - Endpoint: `WebSocket /v1/agent`
  - Target: `wss://agent.deepgram.com/v1/agent`

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository
2. Run the setup script:
   ```
   ./.bin/setup.sh
   ```
   
   This script will:
   - Create a virtual environment
   - Install dependencies
   - Create a default `.env` file if one doesn't exist

3. Alternatively, manually set up the environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python .bin/create_env.py
   ```

4. Update your `.env` file with your actual API keys for OpenAI and Deepgram

## Running the Application

To run the application:

```
python run.py
```

This will start the server on port 8080.

## API Endpoints

### OpenAI Proxy

- `POST /v1/chat/completions` - Proxy for OpenAI's chat completions API

Example:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}'
```

### Deepgram Proxy

- `WebSocket /v1/agent` - WebSocket proxy for Deepgram's voice agent API

## Development

To run in development mode with auto-reload:

```
python run.py
```

The application will use hot reloading in development mode.

## License

[Your license here] 