"""
Dashboard API Server for Nanosecond Arbiter
============================================
Serves the web dashboard AND provides API endpoints for the AI trader
"""

import os
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import shutil
import time
import pandas as pd


# Import Upstox adapter
try:
    from quant_engine.data_upstox import get_upstox_adapter
    UPSTOX_AVAILABLE = True
    # Initialize Streamer Immediately
    print("⏳ Initializing Upstox Streamer...")
    get_upstox_adapter() 
except ImportError:
    UPSTOX_AVAILABLE = False
    print("⚠️ Upstox adapter not available")


# Shared state for trading data - Demo mode with default balances
trading_state = {
    "signal": "HOLD",
    "reasoning": "Demo mode - Connect a trading bot for live data",
    "confidence": 0,
    "balance": 10000.0,  # Demo: $10,000 total
    "balance_spot": 5000.0,  # Demo: $5,000 spot (crypto)
    "balance_futures": 5000.0,  # Demo: $5,000 futures
    "balance_forex": 0.0,
    "balance_indian": 100000.0,  # Demo: ₹1,00,000 Indian market
    "pnl": 0,
    "pnl_spot": 0.0,
    "pnl_futures": 0.0,
    "pnl_forex": 0.0,
    "pnl_indian": 0.0,
    "position": 0,
    "tradesCount": 0,
    "trade": None,
    # Margin fields for all markets
    "margin_spot": 0.0,  # Crypto margin used
    "margin_futures": 0.0,
    "margin_indian": 0.0,  # Indian market margin used
    "available_spot": 5000.0,
    "available_futures": 5000.0,
    "available_indian": 100000.0,
    # New fields for detailed view
    "positions": {},  # Format: {symbol: {entry_price, current_price, quantity, capital, pnl, pnl_percent}}
    "open_orders": [],
    "recent_trades": [],
    "demo_mode": True,  # Flag to indicate demo balances
    
    # ============================================================
    # LATENCY-SAFE ARCHITECTURE: Data Source & Trading Status
    # ============================================================
    # Data sources: EXCHANGE_WS (live), UPSTOX (live)
    "data_source_crypto": "EXCHANGE_WS",
    "data_source_indian": "UPSTOX" if UPSTOX_AVAILABLE else "DISCONNECTED",
    # Data status: LIVE or OFFLINE
    "data_status_crypto": "LIVE",
    "data_status_indian": "OFFLINE", 
    # Trading enabled only with live data
    "trading_enabled_crypto": True,
    "trading_enabled_indian": False, 
    # Last data update timestamps (ms)
    "last_data_update_crypto": 0,
    "last_data_update_indian": 0,
    # Warning messages
    "data_warning_crypto": "",
    "data_warning_indian": "Waiting for Upstox connection...",
}

forex_market_state = {
    "prices": {},  # { "eurusd": { price: 1.05, change: 0.1 } }
    "candles": {}  # { "eurusd": [ { time, open, high, low, close } ] }
}

# Global state for live candle formation (to persist High/Low)
live_candle_state = {} 

state_lock = threading.Lock()


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves static files AND API endpoints"""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory or os.path.join(os.path.dirname(__file__), 'web')
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def end_headers(self):
        self.send_my_headers()
        SimpleHTTPRequestHandler.end_headers(self)

    def send_my_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
    def do_GET(self):
        """Handle GET requests with UTF-8 enforcement"""
        parsed = urlparse(self.path)
        
        # API Endpoints
        if parsed.path.startswith('/api/'):
            if parsed.path == '/api/ai-decision':
                # Add live timestamp so frontend knows we're connected
                response = {**trading_state, "last_update": int(time.time() * 1000)}
                self.send_json_response(response)
            elif parsed.path == '/api/trading-data':
                with state_lock:
                    self.send_json_response(trading_state)
            elif parsed.path == '/api/forex/market-data':
                # Fetch live Indian index prices - SOURCE: UPSTOX ONLY
                indian_prices = {}
                used_upstox = False
                
                # 1. Try Upstox API (LIVE STREAM)
                if UPSTOX_AVAILABLE:
                    try:
                        upstox = get_upstox_adapter()
                        if upstox.is_configured():
                            indian_prices = upstox.get_all_indian_prices()
                            
                            nifty_data = indian_prices.get('nifty', {})
                            banknifty_data = indian_prices.get('banknifty', {})
                            
                            latency = nifty_data.get('feed_latency', 0) if nifty_data else 0
                            
                            if nifty_data or banknifty_data:
                                used_upstox = True
                                price_n = nifty_data.get('price', 0) if nifty_data else 0
                                price_b = banknifty_data.get('price', 0) if banknifty_data else 0
                                print(f"✅ Upstox LIVE: NIFTY={price_n} BANKNIFTY={price_b}")
                    except Exception as e:
                        print(f"⚠️ Upstox API Error: {e}")
                
                # Update trading state based on data source
                with state_lock:
                    # Market Hours Check (Simple IST Check)
                    # Offset +5:30 = 19800 seconds
                    utc_now = time.gmtime()
                    ist_hour = (utc_now.tm_hour + 5 + (1 if utc_now.tm_min + 30 >= 60 else 0)) % 24
                    ist_min = (utc_now.tm_min + 30) % 60
                    
                    # Market Open: 09:15 - 15:30 IST
                    is_market_open = False
                    if 9 <= ist_hour < 16:
                        if ist_hour == 9 and ist_min < 15: is_market_open = False
                        elif ist_hour == 15 and ist_min > 30: is_market_open = False
                        else: is_market_open = True
                    
                    if not is_market_open or not used_upstox:
                         # Force Hydration if store is empty
                         if not indian_prices.get('nifty') or not indian_prices.get('banknifty'):
                             print("🔄 Force Hydrating Store via REST...")
                             if UPSTOX_AVAILABLE:
                                 try:
                                     adapter = get_upstox_adapter()
                                     adapter.get_ltp("NIFTY")
                                     adapter.get_ltp("BANKNIFTY")
                                     indian_prices = adapter.get_all_indian_prices() # Refresh
                                 except Exception as e:
                                     print(f"Hydration Error: {e}")
                    
                    if not is_market_open:
                         trading_state["data_source_indian"] = "UPSTOX"
                         trading_state["data_status_indian"] = "CLOSED"
                         trading_state["trading_enabled_indian"] = False
                         trading_state["data_warning_indian"] = "Market Closed (09:15 - 15:30 IST)"
                         trading_state["indian_feed_latency"] = 0
                         
                    elif used_upstox:
                        # STRICT LATENCY LOCK
                        nifty_lat = indian_prices.get('nifty', {}).get('feed_latency', 0)
                        
                        trading_state["data_source_indian"] = "UPSTOX"
                        trading_state["last_data_update_indian"] = int(time.time() * 1000)
                        trading_state["indian_feed_latency"] = nifty_lat 
                        
                        if nifty_lat > 1000:
                            trading_state["data_status_indian"] = "OFFLINE" # Technically high latency
                            trading_state["trading_enabled_indian"] = False
                            trading_state["data_warning_indian"] = f"HIGH LATENCY: {nifty_lat}ms. Trading Halted."
                        else:
                            trading_state["data_status_indian"] = "LIVE"
                            trading_state["trading_enabled_indian"] = True
                            trading_state["data_warning_indian"] = ""

                    else:
                        trading_state["data_source_indian"] = "DISCONNECTED"
                        trading_state["data_status_indian"] = "OFFLINE"
                        trading_state["trading_enabled_indian"] = False
                        trading_state["data_warning_indian"] = "Upstox feed disconnected. Trading disabled."
                    
                    # Merge with any existing forex prices
                    combined = {**forex_market_state.get("prices", {}), **indian_prices}
                    self.send_json_response(combined)
            elif parsed.path == '/api/forex/candles':
                query = parse_qs(parsed.query)
                symbol = query.get('symbol', [None])[0]
                
                # Special handling for Indian markets - UPSTOX ONLY
                if symbol and symbol.upper() in ["NIFTY", "BANKNIFTY"]:
                    candles = []
                    
                    # 1. Try Upstox if available
                    if UPSTOX_AVAILABLE:
                        try:
                            upstox = get_upstox_adapter()
                            if upstox.is_configured():
                                # Default to 15m for dashboard chart overview
                                candles_data = upstox.get_historical_candles(symbol.upper(), "15minute", 3)
                                if candles_data:
                                    # LIVE UPDATE: Merge current LTP
                                    ltp_data = upstox.get_ltp(symbol.upper())
                                    if ltp_data and ltp_data.get("price") > 0:
                                        current_price = ltp_data["price"]
                                        current_ts = int(time.time())
                                        
                                        # 15-minute bucket
                                        bucket_size = 15 * 60 
                                        current_bucket = current_ts - (current_ts % bucket_size)
                                        # Adjust for IST offset if needed? usually charts expect UTC timestamp or local?
                                        # Existing candles are likely generic epoch. 
                                        # Step 2087 output: 1765878300.
                                        
                                        last_candle = candles_data[-1]
                                        last_ts = 0
                                        # Handle string or int timestamp from Upstox
                                        try:
                                            last_ts = int(last_candle["time"])
                                        except:
                                            pass
                                            
                                        # If last candle is current bucket, update it
                                        if last_ts == current_bucket:
                                            if current_price > last_candle["high"]:
                                                last_candle["high"] = current_price
                                            if current_price < last_candle["low"]:
                                                last_candle["low"] = current_price
                                            last_candle["close"] = current_price
                                        else:
                                            # Append NEW forming candle
                                            # Wait, if last_ts > current_bucket (future?), unlikely.
                                            # If last_ts < current_bucket, we append.
                                            new_candle = {
                                                "time": current_bucket,
                                                "open": current_price,
                                                "high": current_price,
                                                "low": current_price,
                                                "close": current_price,
                                                "volume": 0
                                            }
                                            candles_data.append(new_candle)
                                        
                                    # Convert to dashboard format
                                    candles = candles_data
                        except Exception as e:
                            print(f"⚠️ Upstox Candles Error: {e}")
                            
                    if not candles:
                         self.send_json_response([], status=503) # Service Unavailable
                    else:
                         self.send_json_response(candles)
                
                # Forex / Crypto fallback
                elif symbol and symbol in forex_market_state.get("candles", {}):
                    self.send_json_response(forex_market_state["candles"][symbol])
                else:
                    self.send_json_response([], status=404)
            elif parsed.path == '/api/orderbook':
                self.send_json_response({"asks": [], "bids": []})
            elif parsed.path == '/api/metrics':
                self.send_json_response({
                    "latency": 29,
                    "throughput": 33543877,
                    "ordersProcessed": trading_state.get("tradesCount", 0)
                })
            elif parsed.path == '/api/crypto-decision':
                self.send_json_response({"signals": {"btc": "HOLD", "eth": "HOLD", "sol": "HOLD"}})
            elif parsed.path == '/api/health':
                with state_lock:
                    last_update = trading_state.get("last_update", 0)
                    now = int(time.time() * 1000)
                    is_fresh = (now - last_update) < 5000 if last_update > 0 else False
                    self.send_json_response({
                        "status": "healthy" if is_fresh else "stale",
                        "last_update_ms": last_update,
                        "age_ms": now - last_update if last_update > 0 else -1
                    })
            elif parsed.path == '/api/market/history':
                query = parse_qs(parsed.query)
                symbol = query.get('symbol', ['BTC-USD'])[0]
                interval = query.get('interval', ['15m'])[0]
                try:
                    days_str = query.get('days', ['5'])[0]
                    days = int(days_str)
                except:
                    days = 5
                
                # Handling for Indian markets - UPSTOX ONLY
                if symbol and symbol.upper() in ["NIFTY", "BANKNIFTY"]:
                    if UPSTOX_AVAILABLE:
                        try:
                            upstox = get_upstox_adapter()
                            if upstox.is_configured():
                                # Map interval to Upstox format if needed
                                candles = upstox.get_historical_candles(symbol.upper(), interval, days)
                                
                                # LIVE UPDATE with PERSISTENCE
                                ltp_data = upstox.get_ltp(symbol.upper())
                                if ltp_data and ltp_data.get("price") > 0:
                                    current_price = ltp_data["price"]
                                    current_ts = int(time.time())
                                    
                                    # Map interval to seconds
                                    interval_map = {
                                        "1m": 60, "5m": 300, "15m": 900, "30m": 1800, 
                                        "1h": 3600, "1H": 3600, "4h": 14400, "1d": 86400
                                    }
                                    bucket_size = interval_map.get(interval, 900)
                                    if "minute" in interval:
                                        try:
                                            mins = int(interval.replace("minute", ""))
                                            bucket_size = mins * 60
                                        except: pass
                                        
                                    current_bucket = current_ts - (current_ts % bucket_size)
                                    
                                    if candles:
                                        last_hist = candles[-1]
                                        last_hist_ts = 0
                                        try:
                                            last_hist_ts = int(last_hist["time"])
                                        except: pass
                                        
                                        if last_hist_ts == current_bucket:
                                            # Update History Directly
                                            if current_price > last_hist["high"]: last_hist["high"] = current_price
                                            if current_price < last_hist["low"]: last_hist["low"] = current_price
                                            last_hist["close"] = current_price
                                            
                                            # Update Cache
                                            live_candle_state[(symbol, interval)] = last_hist
                                        else:
                                            # Check Cache for forming candle
                                            cached = live_candle_state.get((symbol, interval))
                                            
                                            if cached and cached["time"] == current_bucket:
                                                # Update Cached
                                                if current_price > cached["high"]: cached["high"] = current_price
                                                if current_price < cached["low"]: cached["low"] = current_price
                                                cached["close"] = current_price
                                                candles.append(cached)
                                            else:
                                                # Create New Candle
                                                new_candle = {
                                                    "time": current_bucket,
                                                    "open": current_price,
                                                    "high": current_price,
                                                    "low": current_price,
                                                    "close": current_price,
                                                    "volume": 0
                                                }
                                                live_candle_state[(symbol, interval)] = new_candle
                                                candles.append(new_candle)

                                    print(f"✅ Upstox Candles: {symbol} {interval} - {len(candles)} candles (Live Included)")
                                    self.send_json_response(candles)
                                    return
                        except Exception as e:
                            print(f"⚠️ Upstox Candles Error: {e}")
                            
                    # If Upstox failed or not available, return error/empty
                    self.send_json_response([], status=503)
                    return
                
                # Non-Indian markets? Currently not supported properly without Yahoo/exchange
                # Returning empty for now to be safe
                self.send_json_response([], status=404)
            else:
                self.send_error(404, "Endpoint not found")
            return

        # Static File Serving with forced UTF-8
        path = self.translate_path(self.path)
        
        # Handle directory index
        if os.path.isdir(path):
            for index in ["index.html", "index.htm"]:
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
        
        ctype = self.guess_type(path)
        
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return
            
        self.send_response(200)
        self.send_header("Content-type", ctype + "; charset=utf-8")
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        self.copyfile(f, self.wfile)
        f.close()

    def do_POST(self):
        """Handle POST requests from the Python trader"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/ai-decision':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
                with state_lock:
                    # Special handling to prevent overwriting of distinct balances
                    if "balance_spot" in data: trading_state["balance_spot"] = data["balance_spot"]
                    if "balance_futures" in data: trading_state["balance_futures"] = data["balance_futures"]
                    if "balance_indian" in data: trading_state["balance_indian"] = data["balance_indian"]
                    
                    if "pnl_spot" in data: trading_state["pnl_spot"] = data["pnl_spot"]
                    if "pnl_futures" in data: trading_state["pnl_futures"] = data["pnl_futures"]
                    if "pnl_indian" in data: trading_state["pnl_indian"] = data["pnl_indian"]
                    
                    # ---------------------------------------------------------
                    # SAFE POSITION MERGING (Crypto vs Indian)
                    # ---------------------------------------------------------
                    if "positions" in data:
                        new_pos = data["positions"]
                        current_pos = trading_state.get("positions", {}).copy()
                        
                        # Determine source of update
                        # If "signal" is INDIAN_FO, we assume these are Indian positions
                        is_indian_update = data.get("signal") == "INDIAN_FO"
                        
                        # Filter existing positions:
                        # If update is Indian, keep only NON-Indian positions from state
                        # If update is Crypto, keep only Indian positions from state
                        kept_pos = {}
                        for sym, p in current_pos.items():
                            is_indian_sym = sym in ["NIFTY", "BANKNIFTY"]
                            if is_indian_update and not is_indian_sym:
                                kept_pos[sym] = p
                            elif not is_indian_update and is_indian_sym:
                                kept_pos[sym] = p
                                
                        # Merge kept positions with new positions
                        final_pos = {**kept_pos, **new_pos}
                        trading_state["positions"] = final_pos
                    
                    # Update other fields generally (skip special ones handled above)
                    skip_keys = [
                        "balance_spot", "balance_futures", "balance_forex", "balance_indian",
                        "pnl_spot", "pnl_futures", "pnl_forex", "pnl_indian",
                        "positions" 
                    ]
                    
                    for k, v in data.items():
                        if k not in skip_keys:
                            trading_state[k] = v
                    
                    # Aggregate total balance
                    s = trading_state.get("balance_spot", 0)
                    f = trading_state.get("balance_futures", 0)
                    fx = trading_state.get("balance_forex", 0)
                    ind = trading_state.get("balance_indian", 0)
                    trading_state["balance"] = s + f + fx + ind
                    
                    # Aggregate total PnL
                    ps = trading_state.get("pnl_spot", 0)
                    pf = trading_state.get("pnl_futures", 0)
                    pfx = trading_state.get("pnl_forex", 0)
                    pind = trading_state.get("pnl_indian", 0)
                    trading_state["pnl"] = ps + pf + pfx + pind
                    
                    # Track last update time for health checks
                    trading_state["last_update"] = int(time.time() * 1000)
                self.send_json_response({"status": "ok"})
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)
        elif parsed.path == '/api/forex/update':
            # Receive Forex Market Data from Bot
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                with state_lock:
                    if "prices" in data: forex_market_state["prices"] = data["prices"]
                    if "candles" in data: forex_market_state["candles"] = data["candles"]
                self.send_json_response({"status": "ok"})
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)

        elif parsed.path == '/api/order':
            # Accept order submissions
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            self.send_json_response({"status": "ok", "message": "Order received"})
        else:
            self.send_json_response({"error": "Not found"}, status=404)
    
    def send_json_response(self, data, status=200):
        """Send a JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        body = json.dumps(data).encode('utf-8')
        self.send_header('Content-Length', str(len(body)))

        self.end_headers()
        self.wfile.write(body)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)

        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress logging for cleaner output"""
        try:
            # Only filter if we have args and the first one is a string containing /api/
            if args and isinstance(args[0], str) and '/api/' in args[0]:
                pass  # Don't log API calls
            else:
                super().log_message(format, *args)
        except:
            super().log_message(format, *args)


if __name__ == '__main__':
    # Start the server on port 8083 to bypass cache
    port = 8083
    
    # Change into web directory
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    if os.path.exists(web_dir):
        os.chdir(web_dir)
        
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    
    print(f"============================================================")
    print(f"⚡ NANOSECOND ARBITER - DASHBOARD SERVER")
    print(f"============================================================")
    print(f"")
    print(f"🌐 Dashboard server running at http://localhost:{port}")
    print(f"📊 Open your browser to see live P&L updates!")
    print("=" * 60)
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
