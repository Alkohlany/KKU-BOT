#!/bin/bash

echo "Starting KKU Bot services..."

# Start the bot in background
python -m bot.main &
BOT_PID=$!

# Start the API server
uvicorn bot.api.main:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!

# Handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill $BOT_PID 2>/dev/null
    kill $API_PID 2>/dev/null
    wait
}

trap cleanup SIGTERM SIGINT

echo "Bot PID: $BOT_PID"
echo "API PID: $API_PID"

# Wait for either process to exit
wait -n $BOT_PID $API_PID
