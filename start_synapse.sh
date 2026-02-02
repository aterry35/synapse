#!/bin/bash

# Synapse One-Button Start Script

# Function to kill processes on exit
cleanup() {
    echo "Stopping Synapse..."
    pkill -P $$
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "========================================"
echo "   SYNAPSE v2.2 - ORCHESTRATOR START    "
echo "========================================"

# Check if port 8000 is in use
if lsof -i :8000 > /dev/null; then
    echo "Port 8000 is busy. Attempting to free it..."
    kill $(lsof -t -i:8000) 2>/dev/null
fi

# Explicitly kill old python processes to prevent conflicts
echo "[*] Cleaning up old processes..."
pkill -f run_bot.py || true
pkill -f "uvicorn app.main:app" || true
sleep 2

# 1. Start Backend Server
echo "[*] Launching Backend Server (Uvicorn)..."
python3 -m uvicorn app.main:app --reload &
BACKEND_PID=$!

# Wait a moment for server to initialize
sleep 2

# 2. Start Telegram Bot
echo "[*] Launching Telegram Bot..."
python3 run_bot.py &
BOT_PID=$!

echo "========================================"
echo "   SYSTEM RUNNING"
echo "   Dashboard: http://127.0.0.1:8000/"
echo "   Press Ctrl+C to Stop All Services"
echo "========================================"

# Wait for processes
wait $BACKEND_PID $BOT_PID
