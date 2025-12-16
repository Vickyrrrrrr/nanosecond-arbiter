import pandas as pd
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode

PRECISION_MAP = {
    "BTCUSDT": 5, # Spot often has higher precision
    "ETHUSDT": 4, 
    "SOLUSDT": 2
}

class SpotExecution:
    def __init__(self, api_key, api_secret, testnet=True):
        self.key = api_key
        self.secret = api_secret
        if testnet:
            self.base_url = 'https://testnet.binance.vision'
        else:
            self.base_url = 'https://api.binance.com'

    def _sign(self, params):
        query_string = urlencode(params)
        return hmac.new(self.secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_candles(self, symbol, interval, limit=200):
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {'symbol': symbol, 'interval': interval, 'limit': limit}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            df = pd.DataFrame(data, columns=[
                'time', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
            ])
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']].astype(float)
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df
        except Exception as e:
            print(f"⚠️ Error Spot Data {symbol}: {e}")
            return pd.DataFrame()

    def get_balance(self, asset="USDT"):
        try:
            if not self.key: 
                print("⚠️ No Spot API Key -> Returning None")
                return None
            headers = {'X-MBX-APIKEY': self.key}
            params = {'timestamp': int(time.time() * 1000)}
            params['signature'] = self._sign(params)
            
            resp = requests.get(f"{self.base_url}/api/v3/account", params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Debug Balance
                # print(f"DEBUG SPOT BAL: {data}")
                
                 # Find USDT balance
                for bal in data['balances']:
                     if bal['asset'] == 'USDT':
                         free = float(bal['free'])
                         locked = float(bal['locked'])
                         return {
                             "wallet_balance": free + locked,
                             "available_balance": free
                         }
                
                print("⚠️ SPOT USDT NOT FOUND IN LIST")
                return None # Return None if USDT not found (likely partial data)
            return None
        except Exception as e:
            print(f"❌ Balance Error: {e}")
            return None

    def place_order(self, symbol, side, qty, max_retries=3):
        # Spot: BUY only allowed usually in this strat, but SELL for exit
        decimals = PRECISION_MAP.get(symbol, 2)
        qty = round(qty, decimals)
        
        if not self.key: 
            print(f"🚫 SIMULATED SPOT: {side} {qty} {symbol}")
            return {'status': 'SIMULATED'}

        headers = {'X-MBX-APIKEY': self.key}
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': qty,
            'timestamp': int(time.time() * 1000)
        }

        for i in range(max_retries):
            try:
                params['timestamp'] = int(time.time() * 1000)
                params['signature'] = self._sign(params)
                
                resp = requests.post(f"{self.base_url}/api/v3/order", params=params, headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in [502, 504, 429]: 
                    print(f"⚠️ Spot Order Retry {i+1}/{max_retries} due to {resp.status_code}...")
                    time.sleep(1 * (2**i))
                    continue
                else:
                    print(f"❌ Spot Order Error: {resp.text}")
                    return None
            except Exception as e:
                print(f"⚠️ Spot Exception Retry {i+1}/{max_retries}: {e}")
                time.sleep(1 * (2**i))
        
        print(f"❌ FATAL: Spot Execution Failed after {max_retries} retries.")
        return None
