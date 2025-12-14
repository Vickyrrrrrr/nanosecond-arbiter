#!/bin/bash
echo "🚀 Starting Nanosecond Arbiter on Render..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi


# Start Dashboard in background
python3 dashboard_server.py &

# Start Quant Trader
python3 quant_trader.py
