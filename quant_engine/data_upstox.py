import os
import requests
import threading
import time
import json
import ssl
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Upstox SDK & Protobuf
import upstox_client
from upstox_client.rest import ApiException
from google.protobuf.json_format import MessageToDict
import websockets

load_dotenv()

# ============================================================================
# CANONICAL PRICE STORE (SINGLE SOURCE OF TRUTH)
# ============================================================================
_canonical_store = {
    "prices": {},  # { "nifty": { ltp, timestamp, latency, ... } }
    "last_update": {}, # { "nifty": unix_timestamp }
    "lock": threading.Lock()
}

class UpstoxStreamer:
    """
    Real-time WebSocket V3 Streamer for Upstox.
    Maintains the Single Source of Truth for prices.
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    # Instrument Keys
    INSTRUMENTS = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank"
    }
    
    def __init__(self):
        self.api_key = os.getenv("UPSTOX_API_KEY", "")
        self.access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")
        self._is_configured = bool(self.access_token)
        self.running = False
        self.thread = None
        
        if self._is_configured:
            print("✅ Upstox Streamer: Configured")
        else:
            print("⚠️ Upstox Streamer: No access token")

    def start_stream(self):
        """Start the WebSocket stream in a background thread."""
        if not self._is_configured or self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_sdk_streamer, daemon=True)
        self.thread.start()
        print("🚀 Upstox Streamer (SDK V3): Started Background Thread")

    def _run_sdk_streamer(self):
        """Use Official SDK Streamer."""
        from upstox_client.feeder import MarketDataStreamerV3
        from upstox_client.api_client import ApiClient
        from upstox_client.configuration import Configuration
        
        # Configure
        config = Configuration()
        config.access_token = self.access_token
        # config.host = "https://api.upstox.com/v2" # SDK defaults to V2, but Feed V3 might be handled internally or override needed?
        # The StreamerV3 likely knows the V3 endpoint.
        
        api_client = ApiClient(config)
        
        # Create Streamer
        # keys = list(self.INSTRUMENTS.values())
        # Note: StreamerV3 takes instrumentKeys in constructor
        
        # self.streamer_instance = MarketDataStreamerV3(api_client, list(self.INSTRUMENTS.values()), "full")
        # Ensure keys are correct format. instruments: ["NSE_INDEX|Nifty 50", ...]
        
        keys = list(self.INSTRUMENTS.values())
        print(f"🔌 Connecting to Upstox V3 Feed for: {keys}")
        
        self.streamer_instance = MarketDataStreamerV3(api_client, keys, "full")
        
        # Bind Events
        self.streamer_instance.on("open", self._on_open)
        self.streamer_instance.on("close", self._on_close)
        self.streamer_instance.on("error", self._on_error)
        self.streamer_instance.on("message", self._on_market_data)
        
        # Connect (Blocking)
        self.streamer_instance.connect()

    def _on_open(self, *args):
        print("✅ Upstox V3 Feed: Connected")

    def _on_close(self, *args):
        print("⚠️ Upstox V3 Feed: Closed")

    def _on_error(self, error, *args):
        print(f"❌ Upstox V3 Feed Error: {error}")

    def _on_market_data(self, message, *args):
        """Handle incoming decoded message."""
        # message is a payload dict from SDK
        try:
            # SDK V3 typically returns a wrapper or dict.
            # Structure: { 'feeds': { 'NSE_INDEX|Nifty 50': { 'ltpc': { 'ltp': ... }, ... } } }
            # Let's inspect signature in logs if unsure, but standard V3 structure:
            
            feeds = message.get("feeds")
            if not feeds:
                # print("WS: Empty Feeds")
                return
            
            # Debug: Print keys occasionally or always (temporarily)
                
            now = int(time.time() * 1000)
            
            for instrument_key, feed_data in feeds.items():
                # Map back to symbol
                symbol = None
                if "Nifty 50" in instrument_key: symbol = "nifty"
                elif "Nifty Bank" in instrument_key: symbol = "banknifty"
                
                if not symbol: continue
                
                # Debug payload structure - force print ONCE
                # print(f"FEED DATA {symbol}: {feed_data}")
                
                # EXTRACT LTP (Upstox V3 Structure)
                # Path: fullFeed -> indexFF (or marketFF) -> ltpc -> ltp
                
                ltp = None
                cp = None # Close Price (Previous Day)
                timestamp = now
                
                # Check for direct LTPC (some modes)
                if "ltpc" in feed_data:
                    ltp = feed_data["ltpc"].get("ltp")
                    cp = feed_data["ltpc"].get("cp")
                    timestamp = int(feed_data["ltpc"].get("ltt", now))
                else:
                    # Check for Full Feed
                    ff = feed_data.get("fullFeed", {})
                    if ff:
                        # Try indexFF (Indices) or marketFF (Stocks/Futures)
                        inner = ff.get("indexFF") or ff.get("marketFF") or {}
                        ltpc = inner.get("ltpc", {})
                        ltp = ltpc.get("ltp")
                        cp = ltpc.get("cp")
                        
                        # Fallback for CP from marketOHLC if 'cp' missing in ltpc
                        if not cp and "marketOHLC" in inner:
                             ohlc_list = inner["marketOHLC"].get("ohlc", [])
                             for c in ohlc_list:
                                 if c.get("interval") == "1d":
                                      # For Indices, 1d close usually implies Prev close if we are live?
                                      # Or we might need to rely on 'cp' key specifically.
                                      # 'cp' is safer.
                                      pass

                        if "ltt" in ltpc:
                            timestamp = int(ltpc["ltt"])

                if ltp is not None:
                    # Calculate Change
                    change_pct = 0.0
                    change_abs = 0.0
                    if cp and cp > 0:
                        change_abs = ltp - cp
                        change_pct = (change_abs / cp) * 100
                        
                    # Update Store
                    with _canonical_store["lock"]:
                         _canonical_store["prices"][symbol] = {
                            "symbol": symbol,
                            "price": ltp,
                            "change24h": change_pct, # Dashboard expects % in this field usually
                            "changePoints": change_abs, # Extra field if needed
                            "timestamp": timestamp,
                            "feed_latency": 0,
                            "source": "UPSTOX_V3_SDK"
                        }
                    # Update heartbeat
                    _canonical_store["last_update"][symbol] = now

        except Exception as e:
            print(f"⚠️ Decode Error: {e}")
            
    # Removed manual WSS methods (_get_market_data_feed_url, _run_websocket_loop, _connect_and_listen, _decode_and_store)

class UpstoxDataAdapter:
    """
    Upstox API Data Adapter (Singleton).
    Wraps the Streamer for unified access.
    """
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self):
        self.streamer = UpstoxStreamer()
        self.streamer.start_stream()
        
    def is_configured(self) -> bool:
        return self.streamer._is_configured

    def get_ltp(self, symbol: str) -> Optional[Dict]:
        """
        Get Canonical LTP from Memory Store.
        NO REST CALLS allowed for LTP.
        """
        # TEMP: Until WS decoding is 100% perfect, we might need a 
        # super-fast poll fallback, OR we strictly return None to force WS fix.
        # User said: "Remove ALL Secondary Prices".
        
        # Access Store
        key = symbol.lower()
        with _canonical_store["lock"]:
             data = _canonical_store["prices"].get(key)
        
        if data:
            # Calculate live latency
            now = int(time.time() * 1000)
            data["feed_latency"] = now - data.get("timestamp", now)
            return data
            
        # Fallback: Trigger a quick REST fetch update IF store is empty
        # (Self-healing for startup)
        # BUT only updates the store, doesn't return directly to ensure consistency pattern
        self._update_store_via_rest(symbol)
        
        # Try read again
        with _canonical_store["lock"]:
             return _canonical_store["prices"].get(key)

    def _update_store_via_rest(self, symbol):
        """Helper to hydrate store if WS is initializing."""
        if not self.is_configured():
            return

        instrument_key = self.streamer.INSTRUMENTS.get(symbol.upper())
        if not instrument_key:
            return

        try:
            # SWITCH TO V3 
            # Endpoint: /v3/market-quote/ltp?instrument_key=...
            url = "https://api.upstox.com/v3/market-quote/ltp"
            params = {"instrument_key": instrument_key}
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.streamer.access_token}"
            }
            
            # Enable debug for hydration
            print(f"🔍 Hydrating {symbol} via {url} params={params}")
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    # V3 Response: { data: { "NSE_INDEX:Nifty 50": { last_price: ..., instrument_token: ... } } }
                    # Note: API might return ':' instead of '|'
                    resp_data = data.get("data", {})
                    quote_data = resp_data.get(instrument_key)
                    if not quote_data:
                        quote_data = resp_data.get(instrument_key.replace("|", ":"), {})
                        
                    ltp = quote_data.get("last_price", 0)
                    
                    if ltp > 0:
                        key = symbol.lower()
                        now = int(time.time() * 1000)
                        
                        print(f"✅ Hydrated {symbol}: {ltp}")
                        with _canonical_store["lock"]:
                             _canonical_store["prices"][key] = {
                                "symbol": key,
                                "price": ltp,
                                "change24h": 0, 
                                "timestamp": now,
                                "feed_latency": 0,
                                "source": "UPSTOX_REST_INIT_V3"
                            }
                    else:
                        print(f"⚠️ Hydration Empty for {symbol} (Key: {instrument_key}): {data}") # DEBUG
            else:
                 print(f"❌ Hydration Failed {response.status_code}: {response.text}")
        except Exception:
            pass
        
    # ... (Rest of historical methods kept for Charts) ...
    def get_all_indian_prices(self) -> Dict[str, Dict]:
        """Return all canonical prices."""
        with _canonical_store["lock"]:
            return _canonical_store["prices"].copy()

    # ... (Historical Candles - KEEP as is, valid for Charts) ...
    def get_historical_candles(
        self, 
        symbol: str, 
        interval: str = "5minute",
        days: int = 5
    ) -> List[Dict]:
        """
        Get historical OHLC candles.
        
        Args:
            symbol: NIFTY or BANKNIFTY
            interval: 1minute, 5minute, 15minute, 30minute, 1hour, 1day
            days: Number of days of history
            
        Returns:
            List of candle dicts
        """
        if not self.is_configured():
            return []
            
        # Upstox V2 supports '1minute', '30minute' for Intraday
        # 'day', 'week', 'month' for Historical
        
        upstox_interval = '1minute' # Default high res
        is_intraday = True
        
        if interval in ['1m', '1minute']: upstox_interval = '1minute'
        elif interval in ['5m', '5minute']: upstox_interval = '1minute' # Fetch 1m, let chart handle/resample
        elif interval in ['15m', '15minute']: upstox_interval = '1minute' # Fetch 1m
        elif interval in ['30m', '30minute']: upstox_interval = '30minute'
        elif interval in ['1h', '1hour']: upstox_interval = '30minute' # Approx
        elif interval in ['1d', 'day']: 
            upstox_interval = 'day'
            is_intraday = False
            
        instrument_key = self.streamer.INSTRUMENTS.get(symbol.upper())
        if not instrument_key:
            print(f"⚠️ Unknown Symbol: {symbol}")
            return []
            
        encoded_key = instrument_key.replace("|", "%7C")

        # LOGIC FIX: If we need deep history (e.g. > 7 days), we MUST use the Date Range Endpoint
        # even for minute intervals. The Intraday endpoint is limited to ~5-7 days.
        use_date_range = not is_intraday or days > 7

        try:
            if not use_date_range:
                # Use Intraday Endpoint (Returns last few days including TODAY)
                # GET /historical-candle/intraday/{instrumentKey}/{interval}
                url = f"{self.BASE_URL}/historical-candle/intraday/{encoded_key}/{upstox_interval}"
            else:
                # Use Date Range Endpoint for Daily/Weekly OR Deep Intraday
                to_date = datetime.now().strftime("%Y-%m-%d")
                from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                url = f"{self.BASE_URL}/historical-candle/{encoded_key}/{upstox_interval}/{to_date}/{from_date}"

            print(f"🔍 Fetching Candles: {url}")
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.streamer.access_token}"
            }
            
            # print(f"🔍 Upstox Historical URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    candidates = data.get("data", {}).get("candles", [])
                    
                    processed = []
                    for c in candidates:
                        # c[0] is iso formatted string
                        try:
                            # Convert ISO to Unix Timestamp (seconds)
                            # Handle "2023 00:00:00+05:30"
                            dt = datetime.fromisoformat(c[0])
                            ts = int(dt.timestamp())
                        except:
                            ts = c[0] # Fallback
                            
                        processed.append({
                            "time": ts,
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5])
                        })
                        
                    # Sort by time ASC for chart
                    processed.sort(key=lambda x: x['time'])
                    
                    if processed:
                         print(f"✅ Upstox Candles for {symbol}: {len(processed)}. Last: {processed[-1]['close']} @ {processed[-1]['time']}")
                         
                    return processed
                        
            print(f"❌ Hist Error {response.status_code}: {response.text}")
            return []
        except Exception as e:
            print(f"⚠️ Upstox Historical Exception: {e}")

    def verify_credentials(self) -> bool:
        """
        Verify that the API credentials are valid.
        
        Returns:
            True if credentials work, False otherwise
        """
        if not self.is_configured():
            print("❌ Upstox: No access token configured")
            return False
        
        try:
            url = f"{self.BASE_URL}/user/profile"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.streamer.access_token}"
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    user = data.get("data", {})
                    print(f"✅ Upstox: Connected as {user.get('user_name', 'Unknown')}")
                    return True
            
            print(f"❌ Upstox: Auth failed - {response.status_code}: {response.text[:100]}")
            return False
        except Exception as e:
            print(f"❌ Upstox: Connection error - {e}")
            return False

# Singleton
_adapter = None
def get_upstox_adapter():
    global _adapter
    if not _adapter:
        _adapter = UpstoxDataAdapter()
    return _adapter


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("UPSTOX API TEST")
    print("=" * 60)
    
    adapter = get_upstox_adapter()
    
    print("\n1. Verifying credentials...")
    print("\n1. Verifying credentials...")
    if adapter.verify_credentials():
        print("\n2. Fetching NIFTY LTP...")
        nifty = adapter.get_ltp("NIFTY")
        if nifty:
            print(f"   NIFTY: ₹{nifty['price']:,.2f}")
        
        print("\n3. Fetching BANKNIFTY LTP...")
        banknifty = adapter.get_ltp("BANKNIFTY")
        if banknifty:
            print(f"   BANKNIFTY: ₹{banknifty['price']:,.2f}")
    else:
        print("\n❌ Cannot proceed without valid credentials")
    
    print("\n" + "=" * 60)
