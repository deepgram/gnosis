# Gnosis Project Makefile

.PHONY: run run-dev run-prod run-test clean help test lint install format venv examples version

# Variables
HOST = 127.0.0.1
PORT = 8080
APP = app.main:app
LOG_LEVEL = info
PYTHON = python
VENV = venv
VERSION = $(shell grep -m 1 "VERSION" app/config.py | cut -d '"' -f 2)

# Default target - show help
help:
	@echo "Gnosis Project Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make run        - Run the server (development mode with auto-reload)"
	@echo "  make run-dev    - Same as 'make run'"
	@echo "  make run-prod   - Run in production mode (no reload, 4 workers)"
	@echo "  make run-simple - Run Uvicorn directly without extra settings"
	@echo "  make run-script - Run using the run.py script (recommended for development)"
	@echo "  make install    - Install dependencies from requirements.txt"
	@echo "  make venv       - Create virtual environment and install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters (flake8, mypy)"
	@echo "  make format     - Format code with black and isort"
	@echo "  make examples   - List available example scripts"
	@echo "  make run-example EXAMPLE=path/to/example.py - Run a specific example"
	@echo "  make run-conversation - Run continuous conversation example with voice agent"
	@echo "  make version    - Display application version"
	@echo "  make clean      - Remove __pycache__ directories and .pyc files"
	@echo ""
	@echo "Environment:"
	@echo "  HOST = $(HOST)"
	@echo "  PORT = $(PORT)"
	@echo "  APP = $(APP)"
	@echo "  LOG_LEVEL = $(LOG_LEVEL)"

# Development server with auto-reload
run: run-dev

run-dev:
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload --log-level $(LOG_LEVEL)

# Production server with multiple workers
run-prod:
	uvicorn $(APP) --host $(HOST) --port $(PORT) --workers 4 --log-level $(LOG_LEVEL)

# Simple server without extra settings
run-simple:
	uvicorn $(APP) --host $(HOST) --port $(PORT)

# Using the run.py script (includes Rich traceback and structured logging)
run-script:
	$(PYTHON) run.py

# Create virtual environment and install dependencies
venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Activate with: source $(VENV)/bin/activate"
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest

# Run linters
lint:
	flake8 .
	mypy .

# Format code
format:
	black .
	isort .

# List and run examples
examples:
	@echo "Available examples:"
	@find examples -name "*.py" | sort

# Display version
version:
	@echo "Gnosis version: $(VERSION)"

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} +
	find . -name ".coverage" -delete

# Run a specific example (usage: make run-example EXAMPLE=voice_agent/basic.py)
run-example:
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Please specify an example: make run-example EXAMPLE=voice_agent/basic.py"; \
		exit 1; \
	fi
	cd examples && $(PYTHON) $(EXAMPLE)

# Run continuous conversation example with custom message
run-conversation:
	@echo "Running continuous conversation with Deepgram Voice Agent..."
	@read -p "Enter your message (default: Hello, how can I help you today?): " message; \
	if [ -z "$$message" ]; then \
		message="Hello, how can I help you today?"; \
	fi; \
	cd examples/voice_agent && $(PYTHON) continuous_conversation.py --message "$$message" --turns 2 