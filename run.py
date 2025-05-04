#!/usr/bin/env python3
"""Wrapper script for running the Litestar app with Rich and Structlog."""
import os
import sys
import uvicorn
from rich.traceback import install

# Show detailed tracebacks
install(show_locals=True, width=120, suppress=[uvicorn])

# Ensure app module is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import config and logging AFTER setting up path and Rich
from app.config import settings
from app.logging_config import setup_logging, get_uvicorn_log_config

# Set up structured logging
setup_logging(log_level=settings.LOG_LEVEL)

if __name__ == "__main__":
    # Get the Uvicorn logging config
    log_config = get_uvicorn_log_config(log_level=settings.LOG_LEVEL)
    
    # Run the server using import string so reload works
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        log_config=log_config,
    )
