import pandas as pd
import time
from datetime import datetime, time as dtime
import pytz
from quant_engine.data_upstox import get_upstox_adapter

class IndianExecution:
    """
    Indian Market Adapter (NSE/BSE).
    Modes: 'PAPER' (Default), 'LIVE' (Upstox API).
    Enforces SEBI Retail Rules & Timing.
    """
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        self.mode = "PAPER" if testnet else "LIVE"
        self.api_key = api_key
        # Indian Timezone
        self.IST = pytz.timezone('Asia/Kolkata')
        
        # --- CONFIGURATION ---
        self.NSE_MAP = {
            "NIFTY": "NIFTY",
            "BANKNIFTY": "BANKNIFTY"
        }
        
        # Trading Hours (IST)
        self.MARKET_START = dtime(9, 15)
        self.MARKET_END = dtime(15, 30)
        
        # Paper Trading State
        self.balance = 100000.0 # INR 1 Lakh Virtual Capital
        self.positions = {}
        self.current_prices = {}
        self.orders = []
        
        print(f"🇮🇳 Indian Market Adapter Init ({self.mode} Mode). Balance: ₹{self.balance}")

        # Risk State
        self.daily_stats = {} # {symbol: {trades: 0, wins: 0, losses: 0, pnl: 0}}
        self.MAX_TRADES_PER_DAY = 2
        self.MAX_LOSSES_PER_DAY = 1
        
    def reset_daily_stats(self):
        """Call at 9:15 AM to reset counters."""
        self.daily_stats = {}

    def start_new_day_if_needed(self):
        now = datetime.now(self.IST)
        pass

    def check_risk_limits(self, symbol):
        """Returns True if trading allowed."""
        stats = self.daily_stats.get(symbol, {"trades": 0, "losses": 0})
        if stats["trades"] >= self.MAX_TRADES_PER_DAY:
            print(f"⛔ Risk Limit: Max Trades ({self.MAX_TRADES_PER_DAY}) hit for {symbol}")
            return False
        if stats["losses"] >= self.MAX_LOSSES_PER_DAY:
             print(f"⛔ Risk Limit: Max Losses ({self.MAX_LOSSES_PER_DAY}) hit for {symbol}")
             return False
        return True

    def record_trade_result(self, symbol, pnl):
        if symbol not in self.daily_stats:
            self.daily_stats[symbol] = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        
        self.daily_stats[symbol]["trades"] += 1
        self.daily_stats[symbol]["pnl"] += pnl
        if pnl < 0:
            self.daily_stats[symbol]["losses"] += 1
        else:
            self.daily_stats[symbol]["wins"] += 1


    def is_market_open(self):
        """Strict 9:15 AM - 3:30 PM IST check."""
        now_ist = datetime.now(self.IST).time()
        # Simple check, ideally also check weekends/holidays
        return self.MARKET_START <= now_ist <= self.MARKET_END

    def get_candles(self, symbol, interval, limit=100):
        """Fetch OHLVC data from Upstox for Analysis."""
        adapter = get_upstox_adapter()
        if not adapter.is_configured():
            print("⚠️ Upstox not configured")
            return pd.DataFrame()
            
        # Map interval to Upstox format
        # 5m -> 5minute
        u_interval = "5minute"
        if interval == "15m": u_interval = "15minute"
        elif interval == "30m": u_interval = "30minute"
        elif interval == "1h": u_interval = "60minute" # 60minute vs 1hour
        
        try:
            # Estimate days needed for limit
            days = 5
            candles = adapter.get_historical_candles(symbol, u_interval, days)
            
            if not candles:
                return pd.DataFrame()
                
            df = pd.DataFrame(candles)
            if df.empty: return pd.DataFrame()
            
            # Format
            df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert(self.IST)
            df.set_index('datetime', inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"⚠️ Upstox Fetch Error: {e}")
            return pd.DataFrame()


    def get_balance(self, asset="INR"):
        return {
            "wallet_balance": self.balance,
            "available_balance": self.balance, # Margin logic simplified
            "unrealized_pnl": self._calc_unrealized_pnl()
        }
        
    def auto_square_off(self):
        """Force close all positions at 3:15 PM IST."""
        now = datetime.now(self.IST).time()
        # Trigger between 15:15 and 15:30
        sq_start = dtime(15, 15)
        if now >= sq_start and now <= self.MARKET_END and self.positions:
            print("⏰ AUTO SQUARE-OFF TRIGGERED (15:15 PM IST) ⏰")
            # Create copy to iterate
            for sym in list(self.positions.keys()):
                pos = self.positions[sym]
                side = "SELL" if pos['side'] == "LONG" else "BUY"
                print(f"📉 Square Off: {side} {sym}")
                self.place_order(sym, side, pos['quantity'])
                
            # Clear all
            self.positions = {}

    def _calc_unrealized_pnl(self):
        pnl = 0.0
        for sym, pos in self.positions.items():
            curr = self.current_prices.get(sym, pos['entry_price'])
            if pos['side'] == "LONG":
                pnl += (curr - pos['entry_price']) * pos['quantity']
            else:
                pnl += (pos['entry_price'] - curr) * pos['quantity']
        return pnl

    def get_positions(self):
        return list(self.positions.values())

    def place_order(self, symbol, side, qty, reduce_only=False):
        """
        Executes order. 
        If PAPER: Updates internal state.
         # If LIVE: Would call Upstox API.
        """
        if not self.is_market_open() and self.mode == "LIVE":
            print(f"⛔ Market Closed (IST). Rejecting {side} {symbol}")
            return None
            
        price = self.current_prices.get(symbol, 0)
        if price == 0: 
            print("⚠️ No price ref for order")
            return None
            
        print(f"🇮🇳 {self.mode} EXECUTION: {side} {qty} {symbol} @ {price}")
        
        if self.mode == "PAPER":
            # Virtual Fill
            trade_val = price * qty
            
            if side == "BUY" and not reduce_only:
                if trade_val > self.balance:
                    print("❌ Insufficient Funds")
                    return None
                
                # Simple Netting Logic (if short exists, cover it)
                if symbol in self.positions and self.positions[symbol]['side'] == "SHORT":
                     # Covering Short
                     # For simplicity in paper mode, we just square off existing or open new
                     pass 

                self.positions[symbol] = {
                    "symbol": symbol, "side": "LONG", "entry_price": price, "quantity": qty
                }
                
                # For simulated F&O, we treat this as Buying the Future/Option
                # Simulation simplifies margin
                
            elif side == "SELL":
                 if symbol in self.positions:
                     del self.positions[symbol] # Close
                 else:
                     # Opening Short (Futures)
                      self.positions[symbol] = {
                        "symbol": symbol, "side": "SHORT", "entry_price": price, "quantity": qty
                    }
            
            return {"status": "FILLED", "price": price}

        return {"status": "FAILED", "reason": "Live Execution Not Implemented"}

    def set_leverage(self, symbol, lev):
        pass # Not applicable for Indian Cash/F&O in standard API way
