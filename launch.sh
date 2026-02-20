#!/bin/bash
# VFX Turnover Tool — launcher
# Starts the Flask AAF server and opens the web app in the default browser.
#
# Usage: ./launch.sh
#
# Requirements: pip install flask flask-cors pyaaf2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PORT=5000

echo "VFX Turnover Tool"
echo "================="

# Check if Flask server is already running on the expected port
if lsof -Pi :$SERVER_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "AAF server already running on port $SERVER_PORT"
else
    # Verify Python dependencies are installed
    if ! python3 -c "import flask, flask_cors, aaf2" 2>/dev/null; then
        echo ""
        echo "Error: Missing Python dependencies for the AAF server."
        echo "Install them with:"
        echo "  pip install flask flask-cors pyaaf2"
        echo ""
        echo "The web app will open but AAF export will be unavailable."
    else
        echo "Starting AAF server on port $SERVER_PORT..."
        cd "$SCRIPT_DIR"
        python3 server.py &
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
