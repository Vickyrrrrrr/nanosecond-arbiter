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


# Shared state for trading data
trading_state = {
    "signal": "HOLD",
    "reasoning": "Waiting for market data...",
    "confidence": 0,
    "balance": 10000,
    "balance_spot": 5000.0,
    "balance_futures": 5000.0,
    "balance_forex": 10000.0,
    "pnl": 0,
    "pnl_spot": 0.0,
    "pnl_futures": 0.0,
    "pnl_forex": 0.0,
    "position": 0,
    "tradesCount": 0,
    "trade": None,
    # New fields for detailed view
    "positions": {},  # Format: {symbol: {entry_price, current_price, quantity, capital, pnl, pnl_percent}}
    "open_orders": [],
    "recent_trades": []
}

forex_market_state = {
    "prices": {},  # { "eurusd": { price: 1.05, change: 0.1 } }
    "candles": {}  # { "eurusd": [ { time, open, high, low, close } ] }
}

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
                self.send_json_response(trading_state)
            elif parsed.path == '/api/trading-data':
                with state_lock:
                    self.send_json_response(trading_state)
            elif parsed.path == '/api/forex/market-data':
                with state_lock:
                    self.send_json_response(forex_market_state.get("prices", {}))
            elif parsed.path == '/api/forex/candles':
                query = parse_qs(parsed.query)
                symbol = query.get('symbol', [None])[0]
                if symbol and symbol in forex_market_state.get("candles", {}):
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
                    if "pnl_spot" in data: trading_state["pnl_spot"] = data["pnl_spot"]
                    if "pnl_futures" in data: trading_state["pnl_futures"] = data["pnl_futures"]
                    
                    # Update other fields generally
                    for k, v in data.items():
                        if k not in ["balance_spot", "balance_futures", "balance_forex", "pnl_spot", "pnl_futures", "pnl_forex"]:
                            trading_state[k] = v
                    
                    # Aggregate total balance
                    s = trading_state.get("balance_spot", 0)
                    f = trading_state.get("balance_futures", 0)
                    fx = trading_state.get("balance_forex", 0)
                    trading_state["balance"] = s + f + fx
                    
                    # Aggregate total PnL
                    ps = trading_state.get("pnl_spot", 0)
                    pf = trading_state.get("pnl_futures", 0)
                    pfx = trading_state.get("pnl_forex", 0)
                    trading_state["pnl"] = ps + pf + pfx
                    
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
