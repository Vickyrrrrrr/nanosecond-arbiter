#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Nanosecond Arbiter Setup..."

# 1. Update System
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip git

# 2. Install Python Dependencies
echo "🐍 Installing Python libraries..."
pip3 install requests websocket-client

# 3. Setup Systemd Services
echo "⚙️ Configuring Systemd Services..."

# Modify service files to point to correct directory if needed
# (Assumes /home/ubuntu/nanosecond-arbiter)

sudo cp deploy/nanosecond-dashboard.service /etc/systemd/system/
sudo cp deploy/nanosecond-trader.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable nanosecond-dashboard
sudo systemctl enable nanosecond-trader

# 4. Prompt for Keys (Optional)
echo "---------------------------------------------------"
echo "✅ Setup Complete!"
echo ""
echo "⚠️  IMPORTANT: You must set your API KEYS in the service file:"
echo "   sudo nano /etc/systemd/system/nanosecond-trader.service"
echo ""
echo "Then start the services:"
echo "   sudo systemctl start nanosecond-dashboard"
echo "   sudo systemctl start nanosecond-trader"
echo ""
echo "Check status:"
echo "   sudo systemctl status nanosecond-trader"
echo "---------------------------------------------------"
