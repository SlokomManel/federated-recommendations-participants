#!/bin/sh
# Install and run Netflix Participant App
set -e

# Check if .env file exists
if [ ! -f .env ]; then
    echo ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo ".env file created from .env.example."
    else
        echo "Error: .env.example file not found. Cannot create .env file. Exiting..."
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    uv venv -p 3.12
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -e . --quiet

echo ""
echo "Starting FastAPI server on http://0.0.0.0:8082"
uv run python app.py
