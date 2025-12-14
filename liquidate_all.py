import os
import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode

# Parse .env manually to avoid dotenv dependency if not installed
def load_env():
    keys = {}
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    keys[k] = v
    except: pass
    return keys

env_vars = load_env()
BINANCE_API_KEY = env_vars.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = env_vars.get("BINANCE_API_SECRET", "")
BASE_URL = 'https://testnet.binancefuture.com'

def sign(params):
    query_string = urlencode(params)
    return hmac.new(BINANCE_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def close_all_positions():
    # 1. Get Positions
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    params = {'timestamp': int(time.time() * 1000)}
    params['signature'] = sign(params)
    
    resp = requests.get(f"{BASE_URL}/fapi/v2/positionRisk", params=params, headers=headers)
    if resp.status_code != 200:
        print(f"Error fetching positions: {resp.text}")
        return

    positions = [p for p in resp.json() if float(p['positionAmt']) != 0]
    
    if not positions:
        print("✅ No open positions found.")
        return

    print(f"🚨 FOUND {len(positions)} OPEN POSITIONS. CLOSING NOW...")

    for p in positions:
        symbol = p['symbol']
        amt = float(p['positionAmt'])
        side = "SELL" if amt > 0 else "BUY" # Close Long with Sell, Close Short with Buy
        qty = abs(amt)
        
        print(f"Executed Market {side} {qty} {symbol}...")
        
        # Place Market Order
        order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': qty,
            'reduceOnly': 'true',
            'timestamp': int(time.time() * 1000)
        }
        order_params['signature'] = sign(order_params)
        
        res = requests.post(f"{BASE_URL}/fapi/v1/order", params=order_params, headers=headers)
        if res.status_code == 200:
            print(f"✅ CLOSED {symbol}")
        else:
            print(f"❌ FAILED {symbol}: {res.text}")
            
if __name__ == "__main__":
    close_all_positions()
