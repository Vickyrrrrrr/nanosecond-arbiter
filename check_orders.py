"""
Quick script to check your current open orders on Binance Testnet
No login required - uses your API keys
"""

import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode

# Your API credentials
API_KEY = "YOUR_BINANCE_API_KEY_HERE"  # Replace with your actual API key
API_SECRET = "YOUR_BINANCE_API_SECRET_HERE"  # Replace with your actual API secret
BASE_URL = "https://testnet.binance.vision"

def get_signature(params):
    query_string = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_open_orders():
    """Get all open orders"""
    endpoint = "/api/v3/openOrders"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': 'BTCUSDT',
        'timestamp': timestamp
    }
    params['signature'] = get_signature(params)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    return response.json()

def get_account_info():
    """Get account balance"""
    endpoint = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    
    params = {
        'timestamp': timestamp
    }
    params['signature'] = get_signature(params)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    return response.json()

if __name__ == "__main__":
    print("="*60)
    print("📊 BINANCE TESTNET - ACCOUNT STATUS")
    print("="*60)
    
    # Get account balance
    print("\n💰 Account Balance:")
    account = get_account_info()
    for balance in account.get('balances', []):
        free = float(balance['free'])
        locked = float(balance['locked'])
        if free > 0 or locked > 0:
            print(f"   {balance['asset']}: {free:.8f} (Locked: {locked:.8f})")
    
    # Get open orders
    print("\n📋 Open Orders (BTCUSDT):")
    orders = get_open_orders()
    
    if not orders:
        print("   No open orders")
    else:
        for order in orders:
            side = order['side']
            price = float(order['price'])
            qty = float(order['origQty'])
            filled = float(order['executedQty'])
            
            emoji = "📥" if side == "BUY" else "📤"
            print(f"   {emoji} {side}: {qty:.8f} BTC @ ${price:.2f} (Filled: {filled:.8f})")
    
    print("\n" + "="*60)
    print(f"Total Open Orders: {len(orders)}")
    print("="*60)
