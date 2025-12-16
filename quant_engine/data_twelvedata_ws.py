
import json
import threading
import time
import websocket
import os
from dotenv import load_dotenv

load_dotenv()

class TwelveDataWebSocket:
    """
    WebSocket Client for Twelve Data
    - URL: wss://ws.twelvedata.com/v1/quotes/price
    - Handles connection, subscription and auto-reconnect
    - Keeps a local cache of latest prices for UI
    """
    
    WS_URL = "wss://ws.twelvedata.com/v1/quotes/price"
    
    def __init__(self, api_key, symbols):
        self.api_key = api_key.strip() if api_key else ""
        self.symbols = symbols
        
        self.ws = None
        self.running = False
        self.latest_prices = {} 
        self.lock = threading.Lock()
        self.last_msg_time = 0
        self.connected = False
        
        # Mapping: "EURUSD" -> "EUR/USD"
        self.symbol_map = {}
        for s in symbols:
            # Basic heuristic: if len 6 & alpha, likely forex pair "EURUSD" -> "EUR/USD"
            # Indices like "SPX" stay "SPX"
            standard = s.upper().replace("/", "")
            if len(standard) == 6 and standard.isalpha() and "USD" in standard:
                 formatted = f"{standard[:3]}/{standard[3:]}"
            else:
                 formatted = standard
            
            self.symbol_map[formatted] = standard  # API format -> Internal format
            
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        
    def start(self):
        """Start the WebSocket thread."""
        self.running = True
        self.thread.start()
        print("⚡ Twelve Data WebSocket Starting...")
        
    def stop(self):
        """Stop the WebSocket."""
        self.running = False
        if self.ws:
            self.ws.close()
            
    def get_latest_price(self, symbol):
        """Get latest price for a symbol (internal format e.g. EURUSD)."""
        clean_sym = symbol.upper().replace("/", "")
        with self.lock:
            return self.latest_prices.get(clean_sym)
            
    def is_connected(self):
        """Check if WS is alive and receiving data."""
        return self.connected and (time.time() - self.last_msg_time < 60)

    def _on_open(self, ws):
        print("✅ Twelve Data WebSocket Connected")
        self.connected = True
        
        # Subscribe
        subs = list(self.symbol_map.keys())
        msg = {
            "action": "subscribe",
            "params": {
                "symbols": ",".join(subs)
                # "apikey": self.api_key # Try sending without first
            }
        }
        print(f"📡 Subscribing to: {msg['params']['symbols']}")
        ws.send(json.dumps(msg))
        
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.last_msg_time = time.time()
            self.connected = True
            
            if data.get("event") == "price":
                symbol_in = data.get("symbol")
                price = float(data.get("price", 0))
                ts = data.get("timestamp", time.time())
                
                # Convert symbol to internal format
                internal_sym = self.symbol_map.get(symbol_in, symbol_in.replace("/", ""))
                
                with self.lock:
                    self.latest_prices[internal_sym] = {
                        "price": price,
                        "timestamp": ts,
                        "source": "WS"
                    }
                    if internal_sym == "AAPL":
                        print(f"📈 AAPL TICK: {price}")
            elif data.get("event") == "subscribe-status":
                print(f"ℹ️ WS Status: {data}")
                
        except Exception as e:
            print(f"⚠️ WS Message Error: {e}")

    def _on_error(self, ws, error):
        print(f"❌ WS Error: {error}")
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        print("⚠️ WS Closed. Reconnecting...")
        self.connected = False

    def _run_forever(self):
        """Main loop with auto-reconnect."""
        while self.running:
            try:
                # Auth via URL query param
                separator = "&" if "?" in self.WS_URL else "?"
                url = f"{self.WS_URL}{separator}apikey={self.api_key}"
                
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever()
                
                if self.running:
                    time.sleep(10) # Backoff
            except Exception as e:
                print(f"💥 WS Critical Error: {e}")
                time.sleep(30)
