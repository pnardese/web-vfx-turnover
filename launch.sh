#!/bin/bash
# VFX Turnover Tool — launcher
# Starts the Flask AAF server and opens the web app in the default browser.
#
# Usage: ./launch.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
SERVER_PORT=5000

echo "VFX Turnover Tool"
echo "================="

# Check if Flask server is already running on the expected port
if lsof -Pi :$SERVER_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "AAF server already running on port $SERVER_PORT"
else
    if [ ! -x "$VENV_PYTHON" ]; then
        echo "Error: venv not found. Run:"
        echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements_server.txt"
        echo "The web app will open but AAF export will be unavailable."
    else
        echo "Starting AAF server on port $SERVER_PORT..."
        "$VENV_PYTHON" "$SCRIPT_DIR/server.py" &
        SERVER_PID=$!
        disown $SERVER_PID
        echo "AAF server started (PID: $SERVER_PID)"
        # Give the server a moment to initialise
        sleep 1
    fi
fi

echo "Opening app in browser..."
open "$SCRIPT_DIR/index.html"
echo "Done."
