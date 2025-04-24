#!/usr/bin/env python
"""Wrapper script for running the app with Rich's friendly error formatting."""
import uvicorn
from rich.traceback import install

# Install rich traceback handler
install(show_locals=True, width=120, suppress=[uvicorn])

# Import app after Rich setup to catch any import errors
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    ) 