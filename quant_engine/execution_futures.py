import pandas as pd
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode

# Precision map (can be moved to config but kept here for local lookup)
PRECISION_MAP = {
    "BTCUSDT": 3,
    "ETHUSDT": 2,
    "SOLUSDT": 0
}

class FuturesExecution:
    def __init__(self, api_key, api_secret, testnet=True):
        self.key = api_key
        self.secret = api_secret
        if testnet:
            self.base_url = 'https://testnet.binancefuture.com'
        else:
            self.base_url = 'https://fapi.binance.com'

    def _sign(self, params):
        query_string = urlencode(params)
        return hmac.new(self.secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def set_leverage(self, symbol, leverage):
        if not self.key: return
        try:
            headers = {'X-MBX-APIKEY': self.key}
            params = {
                'symbol': symbol,
                'leverage': leverage,
                'timestamp': int(time.time() * 1000)
            }
            params['signature'] = self._sign(params)
            resp = requests.post(f"{self.base_url}/fapi/v1/leverage", params=params, headers=headers)
            if resp.status_code == 200:
                print(f"🔧 Leverage set to {leverage}x for {symbol}")
            else:
                print(f"⚠️ Failed to set leverage for {symbol}: {resp.text}")
        except Exception as e:
            print(f"⚠️ Leverage Error: {e}")

    def get_candles(self, symbol, interval, limit=200):
        try:
            url = f"{self.base_url}/fapi/v1/klines"
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
            print(f"⚠️ Error fetching Futures data for {symbol}: {e}")
            return pd.DataFrame()

    def get_balance(self):
        try:
            if not self.key: 
                print("⚠️ No API Key -> Returning None (No Simulation)")
                return None
            headers = {'X-MBX-APIKEY': self.key}
            params = {'timestamp': int(time.time() * 1000)}
            params['signature'] = self._sign(params)
            
            resp = requests.get(f"{self.base_url}/fapi/v2/account", params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Debug full response if needed
                # print(f"DEBUG FUTURES ACCOUNT: {data}")
                
                return {
                    "wallet_balance": float(data['totalWalletBalance']),
                    "margin_balance": float(data['totalMarginBalance']),
                    "available_balance": float(data['availableBalance']),
                    "margin_used": float(data['totalInitialMargin']),
                    "unrealized_pnl": float(data['totalUnrealizedProfit'])
                }
            return None
        except Exception as e:
            print(f"❌ Balance Error: {e}")
            return None

    def place_order(self, symbol, side, qty, reduce_only=False, max_retries=3):
        decimals = PRECISION_MAP.get(symbol, 3)
        qty = round(qty, decimals)
        
        if not self.key: 
            print(f"🚫 SIMULATED Futures Order: {side} {qty} {symbol}")
            return {'status': 'SIMULATED', 'orderId': '123'}

        headers = {'X-MBX-APIKEY': self.key}
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': qty,
            'timestamp': int(time.time() * 1000)
        }
        if reduce_only:
            params['reduceOnly'] = 'true'

        for i in range(max_retries):
            try:
                # Update timestamp on retry
                params['timestamp'] = int(time.time() * 1000)
                params['signature'] = self._sign(params)
                
                resp = requests.post(f"{self.base_url}/fapi/v1/order", params=params, headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in [502, 504, 429]: # Retryable errors
                    print(f"⚠️ Order Retry {i+1}/{max_retries} due to {resp.status_code}...")
                    time.sleep(1 * (2**i)) # Exponential backoff 1s, 2s, 4s
                    continue
                else:
                    print(f"❌ Futures Order Error: {resp.text}")
                    return None
            except Exception as e:
                print(f"⚠️ Order Exception Retry {i+1}/{max_retries}: {e}")
                time.sleep(1 * (2**i))
        
        print(f"❌ FATAL: Execution Failed after {max_retries} retries for {symbol}")
        return None

    def get_positions(self):
        try:
            if not self.key: return []
            headers = {'X-MBX-APIKEY': self.key}
            params = {'timestamp': int(time.time() * 1000)}
            params['signature'] = self._sign(params)
            
            resp = requests.get(f"{self.base_url}/fapi/v2/positionRisk", params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                active_positions = []
                for p in data:
                    amt = float(p['positionAmt'])
                    if amt != 0:
                        active_positions.append({
                            'symbol': p['symbol'],
                            'amount': amt,
                            'entryPrice': float(p['entryPrice']),
                            'unRealizedProfit': float(p['unRealizedProfit'])
                        })
                return active_positions
            return []
        except Exception as e:
            print(f"❌ Fetch Positions Error: {e}")
            return []
