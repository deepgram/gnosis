#!/bin/bash
# Setup script for Gnosis project

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of script directory)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Setting up Gnosis project..."
echo "Project root: $PROJECT_ROOT"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if uv is installed
if ! command -v uv &>/dev/null; then
    echo "uv is required but not installed. Please install uv and try again."
    echo "For example: 'pip install uv' or 'brew install uv'."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Activating virtual environment..."
    source .venv/Scripts/activate
else
    echo "Unsupported OS. Please activate the virtual environment manually."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    python "$SCRIPT_DIR/create_env.py"
    echo "Please edit the .env file with your API keys."
else
    echo ".env file already exists."
fi

# Install and configure pre-commit
echo "Installing Git hooks with pre-commit..."
uv pip install pre-commit
pre-commit install -t commit-msg -t prepare-commit-msg

echo "Setup complete! Run 'python run.py' to start the server."
