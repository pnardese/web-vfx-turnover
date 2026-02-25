#!/bin/bash
# Launch VFX Turnover Tool locally

PORT=8080
DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill any existing server on that port
lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null

echo "Serving from: $DIR"
echo "URL: http://localhost:$PORT"
echo "Press Ctrl+C to stop"

# Open browser (macOS)
sleep 0.5 && open "http://localhost:$PORT" &

# Start server
cd "$DIR" && python3 -m http.server $PORT
