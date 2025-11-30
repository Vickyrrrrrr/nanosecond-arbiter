"""
MARKET MAKING BOT - Shadow Trading Strategy
============================================
This bot implements a simple market making strategy:
1. Monitor the order book spread
2. Place buy orders slightly below market price
3. Place sell orders slightly above market price
4. Profit from the spread when both sides fill

WARNING: This uses REAL MONEY. Start with testnet first!
"""

import json
import socket
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# ============================================================================
# CONFIGURATION
# ============================================================================

# Binance API Configuration
USE_TESTNET = True  # Set to False for real trading (DANGEROUS!)

if USE_TESTNET:
    BASE_URL = "https://testnet.binance.vision"
    WS_URL = "wss://testnet.binance.vision/ws"
    print("🧪 TESTNET MODE - Using fake money")
else:
    BASE_URL = "https://api.binance.com"
    WS_URL = "wss://stream.binance.com:9443/ws"
    print("💰 LIVE MODE - Using REAL money!")

# YOUR API KEYS (Get from Binance)
API_KEY = "YOUR_BINANCE_API_KEY_HERE"  # Replace with your actual API key
API_SECRET = "YOUR_BINANCE_API_SECRET_HERE"  # Replace with your actual API secret

# Trading Configuration
SYMBOL = "BTCUSDT"
SPREAD_PERCENTAGE = 0.002  # 0.2% spread (increased for better profit)
ORDER_SIZE_USD = 1000  # Size of each order in USD (meets Binance 0.01 BTC minimum)
MAX_POSITION = 500  # Maximum position size in USD
UPDATE_INTERVAL = 5  # Seconds between order updates

# Local Engine Configuration
LOCAL_ENGINE_IP = "127.0.0.1"
LOCAL_ENGINE_PORT = 8083

# ============================================================================
# BINANCE API FUNCTIONS
# ============================================================================

def get_signature(params):
    """Generate HMAC SHA256 signature for Binance API"""
    query_string = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_account_balance():
    """Get current account balance"""
    endpoint = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    
    params = {
        'timestamp': timestamp
    }
    params['signature'] = get_signature(params)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    try:
        response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            balances = {b['asset']: float(b['free']) for b in data['balances'] if float(b['free']) > 0}
            return balances
        else:
            print(f"❌ Error getting balance: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {}

def get_current_price(symbol):
    """Get current market price"""
    endpoint = "/api/v3/ticker/price"
    params = {'symbol': symbol}
    
    try:
        response = requests.get(BASE_URL + endpoint, params=params)
        if response.status_code == 200:
            return float(response.json()['price'])
        return None
    except Exception as e:
        print(f"❌ Error getting price: {e}")
        return None

def place_limit_order(symbol, side, quantity, price):
    """Place a limit order on Binance"""
    endpoint = "/api/v3/order"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': symbol,
        'side': side,  # 'BUY' or 'SELL'
        'type': 'LIMIT',
        'timeInForce': 'GTC',  # Good Till Cancelled
        'quantity': quantity,
        'price': price,
        'timestamp': timestamp
    }
    params['signature'] = get_signature(params)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    try:
        response = requests.post(BASE_URL + endpoint, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Order failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception placing order: {e}")
        return None

def cancel_all_orders(symbol):
    """Cancel all open orders for a symbol"""
    endpoint = "/api/v3/openOrders"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': symbol,
        'timestamp': timestamp
    }
    params['signature'] = get_signature(params)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    try:
        response = requests.delete(BASE_URL + endpoint, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Error cancelling orders: {e}")
        return None

# ============================================================================
# LOCAL ENGINE FUNCTIONS
# ============================================================================

def connect_to_local_engine():
    """Connect to local Rust engine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((LOCAL_ENGINE_IP, LOCAL_ENGINE_PORT))
        print(f"✅ Connected to Local Engine at {LOCAL_ENGINE_IP}:{LOCAL_ENGINE_PORT}")
        return s
    except Exception as e:
        print(f"⚠️  Could not connect to local engine: {e}")
        return None

def send_to_engine(socket, side, price, quantity):
    """Send order to local engine for tracking"""
    if not socket:
        return
    
    order = {
        "id": int(time.time() * 1000000),
        "side": side,
        "price": int(price * 100),
        "quantity": int(quantity)
    }
    
    try:
        message = json.dumps(order) + "\n"
        socket.sendall(message.encode('utf-8'))
    except Exception as e:
        print(f"⚠️  Error sending to engine: {e}")

# ============================================================================
# MARKET MAKING STRATEGY
# ============================================================================

def run_market_maker():
    """Main market making loop"""
    print("\n" + "="*60)
    print("🤖 MARKET MAKING BOT STARTING")
    print("="*60)
    
    # Check API keys
    if API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ ERROR: You need to set your Binance API keys!")
        print("📝 Instructions:")
        print("   1. Go to Binance.com (or testnet.binance.vision for testing)")
        print("   2. Create API keys")
        print("   3. Edit market_maker.py and paste your keys")
        print("   4. Run again")
        return
    
    # Connect to local engine
    engine_socket = connect_to_local_engine()
    
    # Get initial balance
    print("\n💰 Checking account balance...")
    balances = get_account_balance()
    if balances:
        print(f"   Balances: {balances}")
    
    print(f"\n📊 Trading Configuration:")
    print(f"   Symbol: {SYMBOL}")
    print(f"   Spread: {SPREAD_PERCENTAGE * 100}%")
    print(f"   Order Size: ${ORDER_SIZE_USD}")
    print(f"   Update Interval: {UPDATE_INTERVAL}s")
    
    print("\n🚀 Starting market making loop...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get current market price
            current_price = get_current_price(SYMBOL)
            if not current_price:
                print("⚠️  Could not get price, retrying...")
                time.sleep(5)
                continue
            
            # Calculate bid/ask prices
            spread = current_price * SPREAD_PERCENTAGE
            bid_price = round(current_price - spread, 2)
            ask_price = round(current_price + spread, 2)
            
            # Calculate quantity (Binance requires 5 decimals for BTC, minimum 0.01)
            quantity = max(0.01, round(ORDER_SIZE_USD / current_price, 5))
            
            print(f"📈 Market: ${current_price:.2f} | Bid: ${bid_price:.2f} | Ask: ${ask_price:.2f}")
            
            # Cancel existing orders
            cancel_all_orders(SYMBOL)
            
            # Place new buy order
            print(f"   📥 Placing BUY order: {quantity} @ ${bid_price}")
            buy_order = place_limit_order(SYMBOL, 'BUY', quantity, bid_price)
            if buy_order:
                send_to_engine(engine_socket, 'Buy', bid_price, quantity)
            
            # Place new sell order
            print(f"   📤 Placing SELL order: {quantity} @ ${ask_price}")
            sell_order = place_limit_order(SYMBOL, 'SELL', quantity, ask_price)
            if sell_order:
                send_to_engine(engine_socket, 'Sell', ask_price, quantity)
            
            # Wait before next update
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping market maker...")
        print("🧹 Cancelling all orders...")
        cancel_all_orders(SYMBOL)
        print("✅ Shutdown complete")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         MARKET MAKING BOT - Shadow Trading                ║
    ║                                                           ║
    ║  ⚠️  WARNING: This bot trades with REAL money!           ║
    ║  📚 Make sure you understand the risks before running    ║
    ║  🧪 Start with TESTNET mode first (USE_TESTNET = True)   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    run_market_maker()
