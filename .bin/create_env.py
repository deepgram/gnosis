#!/usr/bin/env python
"""
Script to create a .env file with default values.
Run this script to create a default .env file.
"""

import sys
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent.absolute()
# Get the project root directory (parent of script directory)
project_root = script_dir.parent

env_content = """# App Settings
DEBUG=true
VERSION=0.1.0
LOG_LEVEL=INFO
CORS_ORIGINS=["*"]

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Endpoints
OPENAI_BASE_URL=https://api.openai.com
DEEPGRAM_BASE_URL=https://api.deepgram.com

# MCP Settings
MCP_ENABLED=true
"""


def create_env_file():
    """Create a .env file with default values."""
    env_path = project_root / ".env"

    # Check if .env file already exists
    if env_path.exists():
        if len(sys.argv) > 1 and sys.argv[1] == "--force":
            pass  # Skip confirmation if --force flag is provided
        else:
            overwrite = input(
                f".env file already exists at {env_path}. Overwrite? (y/n): "
            )
            if overwrite.lower() != "y":
                print("Operation cancelled.")
                return

    # Write the .env file
    with open(env_path, "w") as f:
        f.write(env_content)

    print(f".env file created successfully at {env_path}.")


if __name__ == "__main__":
    create_env_file()
