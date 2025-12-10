#!/bin/bash
echo "🚀 Starting Nanosecond Arbiter on Render..."

# Start Dashboard in background
python3 dashboard_server.py &

# Start Trader in foreground (so container stays alive)
# Ensure API Keys are set in Render Environment Variables!
python3 safe_trader.py
