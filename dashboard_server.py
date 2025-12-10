"""
Dashboard API Server for Nanosecond Arbiter
============================================
Serves the web dashboard AND provides API endpoints for the AI trader
"""

import os
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse


# Shared state for trading data
trading_state = {
    "signal": "HOLD",
    "reasoning": "Waiting for market data...",
    "confidence": 0,
    "balance": 10000,
    "pnl": 0,
    "position": 0,
    "tradesCount": 0,
    "trade": None,
    # New fields for detailed view
    "positions": {},  # Format: {symbol: {entry_price, current_price, quantity, capital, pnl, pnl_percent}}
    "open_orders": [],
    "recent_trades": []
}

state_lock = threading.Lock()


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves static files AND API endpoints"""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory or os.path.join(os.path.dirname(__file__), 'web')
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/ai-decision':
            self.send_json_response(trading_state)
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
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests from the Python trader"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/ai-decision':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
                with state_lock:
                    trading_state.update(data)
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
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
