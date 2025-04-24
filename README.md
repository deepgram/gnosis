# Gnosis

An intelligence API proxy for OpenAI's Chat Completions API, Deepgram's Voice Agent API, and Model Context Protocol.

## Overview

Gnosis works as a proxy to the OpenAI Chat Completion's API and the Deepgram Voice Agent API. When a user sends a chat completion or connects to an agent, we hijack the config and insert function/tool call configuration. When tool call requests come back from the upstream service, we intercept it, run our built-in tool calls, respond to the service, and then resume the standard proxy.

This application also implements the Model Context Protocol (MCP) for standardized interactions between LLM applications and external data sources/tools.

## Features

- **OpenAI API Proxy**: Forwards requests to OpenAI's Chat Completions API
- **Deepgram API Proxy**: Forwards requests to Deepgram's Voice Agent API
- **Tool Interception**: Intercepts and handles tool calls from AI services
- **MCP Implementation**: Supports the Model Context Protocol for standardized LLM integrations
- **WebSocket Support**: Handles both HTTP and WebSocket connections

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

4. Run the application:
   ```
   python run.py
   ```

## API Endpoints

### OpenAI Proxy

- `POST /v1/chat/completions` - Proxy for OpenAI's chat completions API

### Deepgram Proxy

- `POST /v1/agent` - Proxy for Deepgram's agent API
- `WebSocket /v1/agent/live` - WebSocket proxy for Deepgram's live agent API

### Model Context Protocol (MCP)

- `WebSocket /mcp` - MCP WebSocket endpoint for integration with MCP clients

## Development

To run in development mode with auto-reload:

```
python run.py
```

## License

[Your license here] 