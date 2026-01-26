#!/bin/sh
# Install and run Netflix Participant App
set -e

# Ensure uv is installed (https://docs.astral.sh/uv/)
if ! command -v uv >/dev/null 2>&1; then
    echo ""
    echo "Error: 'uv' not found."
    echo "Installing uv now..."
    echo ""

    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "Error: neither 'curl' nor 'wget' was found, so uv can't be installed automatically."
        echo "Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    # Best-effort: ensure current shell can see ~/.local/bin (common install location)
    if [ -d "$HOME/.local/bin" ]; then
        PATH="$HOME/.local/bin:$PATH"
        export PATH
    fi

    if ! command -v uv >/dev/null 2>&1; then
        echo "uv was installed but is not on PATH in this shell."
        echo "Close and reopen your terminal, then re-run: ./install.sh"
        exit 1
    fi
fi

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
