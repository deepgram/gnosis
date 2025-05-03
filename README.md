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

## Development Setup

### Linting and Code Quality

This project uses pre-commit hooks to automatically check and fix code issues:

1. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```

2. Set up pre-commit hooks:
   ```
   pre-commit install
   ```

The pre-commit hooks will automatically:
- Remove unused imports
- Remove unused variables
- Check code style with flake8

You can also run the checks manually:
```
pre-commit run --all-files
```

Or run autoflake directly:
```
autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive app/
```

3. VS Code will now show linting errors and organize imports on save

For other editors/IDEs, configure their Python linting tools to use flake8 and autoflake.

### File Watcher for Automatic Cleanup

For a more universal solution that works with any editor, we've included a file watcher script that automatically runs autoflake whenever a Python file is saved:

1. Install the watchdog package:
   ```
   pip install watchdog
   ```

2. Run the file watcher script in a separate terminal:
   ```
   python scripts/watch.py
   ```

This will continuously monitor the `app` directory for changes and automatically clean up unused imports and variables in any Python file when it's saved.
