#!/bin/bash
# Setup script for Gnosis project

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Setting up Gnosis project..."
echo "Project root: $PROJECT_ROOT"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Activating virtual environment..."
    source venv/Scripts/activate
else
    echo "Unsupported OS. Please activate the virtual environment manually."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    python "$SCRIPT_DIR/create_env.py"
    echo "Please edit the .env file with your API keys."
else
    echo ".env file already exists."
fi

# Install Git hooks
echo "Installing Git hooks..."
if [ -f "$SCRIPT_DIR/hooks/install-hooks.sh" ]; then
    bash "$SCRIPT_DIR/hooks/install-hooks.sh"
else
    echo "Git hooks installation script not found. Skipping."
fi

echo "Setup complete! Run 'python run.py' to start the server." 