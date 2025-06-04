# Gnosis Project Makefile

.PHONY: run run-dev install

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  run-dev: Run the development server"
	@echo "  install: Install dependencies"
	@echo "  help: Display this help message"

# Development server with auto-reload
run: run-dev

run-dev:
	uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload --log-level debug

# Install dependencies
install:
	pip install -r requirements.txt