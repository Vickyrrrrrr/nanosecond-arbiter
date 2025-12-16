import pandas as pd
import time
import threading
import yfinance as yf

class ForexExecution:
    """
    Non-Crypto Execution Adapter (Forex, Commodities, Indices).
    Source: YAHOO FINANCE (Snapshot Only)
    """
    
    def __init__(self, api_key, api_secret, testnet=True):
        # --- CONFIGURATION: YAHOO FINANCE SYMBOLS ---
        self.YAHOO_MAP = {
            # Forex (X = Global Market)
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "JPY=X",
            
            # Commodities (Futures)
            "XAU/USD": "GC=F",   # Gold Futures
            "XAG/USD": "SI=F",   # Silver Futures
            "WTI": "CL=F",       # Crude Oil
            "BRENT": "BZ=F",     # Brent Crude
            
            # Global Indices
            "SPX": "^GSPC",      # S&P 500
            "NDX": "^IXIC",      # Nasdaq Composite
            "DJI": "^DJI",       # Dow Jones
            "GDAXI": "^GDAXI",   # DAX (Germany)
            "FTSE": "^FTSE",     # FTSE 100 (UK)
            "NI225": "^N225",    # Nikkei 225 (Japan)
            "HSI": "^HSI",       # Hang Seng (HK)
            "SSEC": "000001.SS"  # Shanghai
        }
        
        # Market Groups for Round Robin
        self.ALL_SYMBOLS_DISPLAY = list(self.YAHOO_MAP.keys())
            
        self.balance = 10000.0  # Simulation Balance
        self.positions = {}
        self.current_prices = {} 
        
        # Data Cache
        self.data_cache = {
            "prices": {},
            "candles": {},
            "data_source": "YAHOO_FINANCE_REST",
            "last_update": 0
        }
        self.cache_lock = threading.Lock()
        
        # Loop Config
        self.running = True
        self.SNAPSHOT_INTERVAL = 30  # Update every 30 seconds (Aggressive)
        self.symbol_last_update = {s: 0 for s in self.ALL_SYMBOLS_DISPLAY}
        
        self.thread = threading.Thread(target=self._market_data_loop, daemon=True)
        self.thread.start()

    def _market_data_loop(self):
        """
        Smart Polling Loop for Yahoo Finance.
        - Fast Interval (15s): Forex, US Indices.
        - Slow Interval (60s): Commodities, Global Indices (Delayed).
        - Rate Limit: 1 request every 0.5s min.
        """
        # Fast: Forex + US Indices (Real-ish time)
        FAST_SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "SPX", "NDX", "DJI"]
        FAST_INTERVAL = 15
        
        # Slow: Commodities + International (Delayed)
        SLOW_INTERVAL = 60
        
        iterator_idx = 0
        
        while self.running:
            try:
                now = time.time()
                
                # Round Robin Selection
                total_syms = len(self.ALL_SYMBOLS_DISPLAY)
                if total_syms > 0:
                    sym_display = self.ALL_SYMBOLS_DISPLAY[iterator_idx % total_syms]
                    
                    # Determine required interval
                    required_interval = FAST_INTERVAL if sym_display in FAST_SYMBOLS else SLOW_INTERVAL
                    
                    # Check age
                    last_up = self.symbol_last_update.get(sym_display, 0)
                    age = now - last_up
                    
                    if age > required_interval:
                        ticker = self.YAHOO_MAP.get(sym_display)
                        
                        # Fetch
                        print(f"🌍 Yahoo Poll ({sym_display}): Age={age:.1f}s (Target: {required_interval}s)...")
                        self._update_yahoo_snapshot(sym_display, ticker)
                        self.symbol_last_update[sym_display] = time.time() # Update time AFTER fetch attempt
                        
                        iterator_idx += 1
                        time.sleep(0.5) # Rate Limit: 2 req/sec max (Safe)
                    else:
                        iterator_idx += 1
                        time.sleep(0.05) # Skip fast if not ready
                else:
                    time.sleep(1)
                               
            except Exception as e:
                print(f"⚠️ Yahoo Loop Error: {e}")
                time.sleep(5)
                
    def _update_yahoo_snapshot(self, display_name, ticker):
        """Fetch Price + Calculate Daily Change (24h) using Yahoo Finance Fast Info."""
        try:
            t = yf.Ticker(ticker)
            
            # FAST INFO METHOD (Primary for Snapshot)
            # Provides authoritative 'previous_close' and 'last_price'
            info = t.fast_info
            
            price = 0.0
            prev_close = 0.0
            change = 0.0
            
            try:
                price = getattr(info, 'last_price', 0.0)
                prev_close = getattr(info, 'previous_close', 0.0)
            except:
                price = 0.0 # Trigger fallback
            
            # If fast_info valid
            if price > 0 and prev_close > 0:
                change = ((price - prev_close) / prev_close) * 100
                self.current_prices[display_name] = price
                
            else:
                 # Fallback to History (Candles)
                print(f"⚠️ FastInfo missing for {ticker}, falling back to history...")
                df = t.history(period="5d", interval="1d")
                if not df.empty:
                    latest = df.iloc[-1]
                    price = float(latest['Close'])
                    self.current_prices[display_name] = price
                    
                    if len(df) > 1:
                        prev = df.iloc[-2]
                        prev_close = float(prev['Close'])
                        if prev_close > 0:
                            change = ((price - prev_close) / prev_close) * 100
                    else:
                        open_price = float(latest['Open'])
                        if open_price > 0:
                            change = ((price - open_price) / open_price) * 100

            if price > 0:
                key = display_name.replace("/", "").lower()
                with self.cache_lock:
                    self.data_cache["prices"][key] = {
                        "symbol": display_name,
                        "proxy": None,
                        "price": price,
                        "change24h": change,
                        "dataSource": "YAHOO_FINANCE",
                        "status": "SNAPSHOT",
                        "lastUpdate": int(time.time() * 1000)
                    }
                    self.data_cache["last_update"] = int(time.time() * 1000)
                    print(f"✅ Updated {display_name}: {price:.4f} (Change: {change:+.2f}%)")
            else:
                 print(f"⚠️ No data for {ticker}")

        except Exception as e:
            print(f"❌ Yahoo Snapshot Failed {display_name}: {e}")

    def get_candles(self, symbol, interval, limit=100):
        # ... Stub for strategy compat ...
        return pd.DataFrame()

    def get_balance(self, asset="USD"):
        # Real Analysis PnL
        unrealized = 0.0
        # ... (Simplified for Simulation) ...
        return {
            "wallet_balance": self.balance,
            "available_balance": self.balance, 
            "unrealized_pnl": unrealized,
            "margin_used": 0.0
        }

    def get_positions(self):
        return list(self.positions.values()) if isinstance(self.positions, dict) else self.positions

    def place_order(self, symbol, side, qty, reduce_only=False):
        # Simulation Mode
        price = self.current_prices.get(symbol, 0.0)
        status = "FILLED" if price > 0 else "FAILED"
        if status == "FILLED":
            print(f"📝 SIM EXEC {side} {symbol} @ {price}")
        return {"status": status, "price": price}

    def set_leverage(self, symbol, lev):
        pass 
        
    def get_market_snapshot(self):
        with self.cache_lock:
            import copy
            return copy.deepcopy(self.data_cache)
