#!/bin/bash

echo "Starting KKU Bot services..."

# Start the bot in background
python -m bot.main &
BOT_PID=$!

# Start the API server
uvicorn bot.api.main:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!

echo "Bot PID: $BOT_PID, API PID: $API_PID"

# Graceful shutdown handler
graceful_shutdown() {
    echo "Shutting down gracefully..."
    kill -TERM $BOT_PID 2>/dev/null
    kill -TERM $API_PID 2>/dev/null
    wait $BOT_PID 2>/dev/null
    wait $API_PID 2>/dev/null
    echo "Shutdown complete"
    exit 0
}

trap graceful_shutdown SIGTERM SIGINT

# Wait for any process to exit, then kill the other
wait -n
EXIT_CODE=$?
echo "A process exited with code $EXIT_CODE. Shutting down..."
kill -TERM $BOT_PID $API_PID 2>/dev/null
wait $BOT_PID $API_PID 2>/dev/null
exit $EXIT_CODE
