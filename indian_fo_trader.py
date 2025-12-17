"""
Indian F&O Trader Bot
=====================
Intraday trading bot for NIFTY & BANKNIFTY F&O.

SEBI compliant - Intraday only, no overnight.
Uses Yahoo Finance for price data (paper trading).

Usage:
    python indian_fo_trader.py
"""

import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
import datetime as dt
from datetime import datetime, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv
import pytz

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_engine.strategy_indian_fo import (
    IndianFOStrategy,
    Direction,
    SignalType,
    TradeType,
    IndianFOSignal,
    InstrumentType
)

from quant_engine.data_upstox import get_upstox_adapter

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')

# ============================================================================
# CONFIGURATION
# ============================================================================

DASHBOARD_URL = "http://localhost:8083/api/ai-decision"
ANALYSIS_INTERVAL = 60  # Every 60 seconds

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK"
}

STARTING_CAPITAL = 100000.0  # ₹1 Lakh paper trading


# ============================================================================
# DATA FETCHING (UPSTOX - LIVE)
# ============================================================================

# Risk Management Configuration (MANDATORY)
MAX_PER_TRADE_CAPITAL = 25000.0  # Max ₹25k per trade
RISK_PER_TRADE_PCT = 0.01        # Max 1% risk per trade
DAILY_LOSS_LIMIT_PCT = 0.02      # Stop if daily loss >= 2%
MAX_CONCURRENT_TRADES = 1        # Max 1 active trade

# CLEAN ARCHITECTURE: UPSTOX ONLY

upstox = get_upstox_adapter()
if upstox.is_configured() and upstox.verify_credentials():
    DATA_SOURCE = "UPSTOX"
    TRADING_ENABLED = True
    print("\n✅ UPSTOX Connection Verified: Ready for Trading")
else:
    print("\n❌ CRITICAL: UPSTOX NOT CONFIGURED")
    print("This bot requires a valid Upstox connection to function.")
    print("Exiting...")
    sys.exit(1)

def get_candles(symbol: str, interval: str = "5m", days: int = 1) -> pd.DataFrame:
    """Fetch candlestick data from UPSTOX only."""
    
    # -------------------------------------------------------------
    # UPSTOX (Real-Time for Trading)
    # -------------------------------------------------------------
    adapter = get_upstox_adapter()
    # Map interval to Upstox format
    interval_map = {
        "1m": "1minute", 
        "5m": "1minute", # Fallback to 1m as 5m not supported by V2
        "15m": "30minute", # Fallback to closest
        "30m": "30minute"
    }
    upstox_interval = interval_map.get(interval, "1minute")
    
    candles = adapter.get_historical_candles(symbol, upstox_interval, days)
    if not candles:
        return pd.DataFrame()
    
    df = pd.DataFrame(candles)
    if df.empty:
        return pd.DataFrame()
        
    # Format index as datetime with IST timezone
    df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert(IST)
    df.set_index('datetime', inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]


# ============================================================================
# TRADER BOT
# ============================================================================

class IndianFOTrader:
    """
    Indian F&O Intraday Trading Bot.
    
    - NIFTY & BANKNIFTY only
    - No indicators
    - Opening Range breakout
    - IST trading hours
    """
    
    def __init__(self):
        # Initialize strategies
        self.strategies = {
            "NIFTY": IndianFOStrategy("NIFTY"),
            "BANKNIFTY": IndianFOStrategy("BANKNIFTY")
        }
        
        # Portfolio
        self.capital = STARTING_CAPITAL
        self.start_capital = STARTING_CAPITAL
        
        # Positions by symbol
        self.positions: Dict[str, Dict] = {}
        
        # P&L tracking
        self.nifty_pnl = 0.0
        self.banknifty_pnl = 0.0
        self.total_pnl = 0.0
        
        # Trade tracking
        self.trades_today = {"NIFTY": 0, "BANKNIFTY": 0}
        self.wins = {"NIFTY": 0, "BANKNIFTY": 0}
        self.losses = {"NIFTY": 0, "BANKNIFTY": 0}
        
        # Daily reset tracking
        self.last_reset_date = None
        
        print(f"\n{'='*60}")
        print(f"🇮🇳 INDIAN F&O BREAKOUT TRADER")
        print(f"{'='*60}")
        print(f"Instruments: NIFTY 50, BANK NIFTY")
        print(f"Capital: ₹{self.capital:,.0f}")
        print(f"Trading Hours: 09:20 - 15:20 IST")
        print(f"NO indicators - Only price, structure, volatility")
        print(f"{'='*60}")
        
        # LATENCY-SAFE ARCHITECTURE WARNING

    def can_take_new_trade(self) -> bool:
        """
        Check global constraints: Concurrency & Daily Loss.
        """
        # 1. Concurrency Check
        if len(self.positions) >= MAX_CONCURRENT_TRADES:
            print(f"   🚫 RISK: Max Concurrent Trades Reached ({MAX_CONCURRENT_TRADES})")
            return False

        # 2. Daily Loss Limit Check
        # Loss is negative in self.total_pnl, so we check if it exceeds limit
        daily_loss_limit = self.start_capital * DAILY_LOSS_LIMIT_PCT
        if self.total_pnl <= -daily_loss_limit:
            print(f"   🚫 RISK: Daily Loss Limit Hit (₹{abs(self.total_pnl):,.0f} >= ₹{daily_loss_limit:,.0f})")
            return False
            
        return True

    def calculate_safe_position_size(self, symbol: str, entry: float, stop_loss: float):
        """
        Calculate safe position size based on:
        1. Max Capital Cap (₹25k)
        2. Max Risk Cap (1% of Total Capital)
        
        Returns: (quantity, lots, capital_used)
        """
        lot_size = 50 if symbol == "NIFTY" else 25 
        
        # 1. Capital Constraint: Min(₹25k, Available Balance)
        available_balance = self.capital
        max_trade_cap = min(MAX_PER_TRADE_CAPITAL, available_balance)
        
        max_qty_by_cap = int(max_trade_cap / entry)
        
        # 2. Risk Constraint: 1% of Total Capital
        risk_per_trade = self.start_capital * RISK_PER_TRADE_PCT
        stop_loss_diff = abs(entry - stop_loss)
        
        if stop_loss_diff == 0:
            max_qty_by_risk = 0
        else:
            max_qty_by_risk = int(risk_per_trade / stop_loss_diff)
            
        # 3. Select Safest
        safe_qty = min(max_qty_by_cap, max_qty_by_risk)
        
        # Round down to nearest lot
        lots = safe_qty // lot_size
        final_qty = lots * lot_size
        
        capital_required = final_qty * entry
        risk_exposure = final_qty * stop_loss_diff
        
        if lots < 1:
            print(f"   ⚠️ SIZING: 0 Lots. Cap limit: {max_qty_by_cap}, Risk limit: {max_qty_by_risk}")
            print(f"      Entry: {entry}, SL Diff: {stop_loss_diff}, Cap: {max_trade_cap}")
            return 0, 0, 0
            
        print(f"   🛡️ SIZING: {lots} lots ({final_qty} units)")
        print(f"      Capital: ₹{capital_required:,.0f} (Limit: ₹{max_trade_cap:,.0f})")
        print(f"      Risk:    ₹{risk_exposure:,.0f} (Limit: ₹{risk_per_trade:,.0f})")
        
        return final_qty, lots, capital_required
    
    def check_daily_reset(self):
        """Reset daily state at market open."""
        today = datetime.now(IST).date()
        
        if self.last_reset_date != today:
            for strategy in self.strategies.values():
                strategy.reset_daily_state()
            
            self.trades_today = {"NIFTY": 0, "BANKNIFTY": 0}
            self.nifty_pnl = 0.0
            self.banknifty_pnl = 0.0
            self.last_reset_date = today
            print(f"🔄 Daily reset complete for {today}")
    
    def is_trading_time(self) -> bool:
        """Check if within trading hours."""
        now = datetime.now(IST).time()
        # Weekday check (Mon=0, Sun=6)
        if datetime.now(IST).weekday() >= 5:
            return False
        # Check if within market hours (9:15 to 15:30)
        return dt.time(9, 15) <= now <= dt.time(15, 30)
    
    def run_analysis(self):
        """Run analysis cycle."""
        now = datetime.now(IST)
        print(f"\n{'─'*60}")
        print(f"📊 ANALYSIS @ {now.strftime('%H:%M:%S')} IST")
        print(f"{'─'*60}")
        
        # Check daily reset
        self.check_daily_reset()
        
        # Check if market hours
        if not self.is_trading_time():
            print("⏰ Outside trading hours (09:20-15:20 IST)")
            return
        
        # Check for mandatory exits
        self.check_mandatory_exits()
        
        # Analyze each instrument
        for symbol in ["NIFTY", "BANKNIFTY"]:
            self.analyze_symbol(symbol)
        
        # Update dashboard
        self.update_dashboard()
        
        # Print status
        self.print_status()
    
    def analyze_symbol(self, symbol: str):
        """Analyze and potentially trade a symbol."""
        if symbol in self.positions:
            self.check_exit(symbol)
            return
        
        strategy = self.strategies[symbol]
        
        # -------------------------------------------------------------
        # STRICT LATENCY CHECK
        # -------------------------------------------------------------
        adapter = get_upstox_adapter()
        ltp_data = adapter.get_ltp(symbol)
        
        if not ltp_data:
            print(f"   🚫 {symbol}: No Canonical Data (Wait for Stream)")
            return
            
        latency = ltp_data.get("feed_latency", 9999)
        if latency > 1000:
            print(f"   🚫 {symbol}: High Latency ({latency}ms) - SKIPPING")
            return
            
        # -------------------------------------------------------------
        # Fetch Candles
        # -------------------------------------------------------------
        df_5m = get_candles(symbol, "5m", 1)
        df_15m = get_candles(symbol, "15m", 1)
        
        if df_5m.empty:
            print(f"   {symbol}: No data")
            return
        
        # Generate signal
        signal = strategy.generate_signal(df_5m, df_15m if not df_15m.empty else None)
        
        if signal:
            # LATENCY-SAFE GUARD: Block execution if using delayed data
            if not TRADING_ENABLED:
                print(f"   🚫 {symbol}: Signal detected ({signal.trade_type.value}) but TRADING DISABLED - using delayed data")
                return
            
            # RISK CHECK 1: Global Constraints
            if not self.can_take_new_trade():
                print(f"   🚫 {symbol}: Global Constraints (Max Trades/Loss) Reached")
                return

            # RISK CHECK 2: Position Sizing
            # Calculate quantity based on strictly defined risk rules
            qty, lots, capital_required = self.calculate_safe_position_size(symbol, signal.entry_price, signal.stop_loss)
            
            if qty == 0:
                print(f"   🚫 {symbol}: Trade Skipped - Position Sizing Violation (Risk/Capital Limit)")
                return

            self.execute_signal(signal, qty, lots, capital_required)
        else:
            print(f"   ⚪ {symbol}: No Signal (Checks: Structure, Breakout, Volatility, Wicks)")
            or_struct = strategy.opening_range
            if or_struct and or_struct.is_complete:
                print(f"      OR High: ₹{or_struct.range_high:.0f} | Low: ₹{or_struct.range_low:.0f}")
    
    def execute_signal(self, signal: IndianFOSignal, qty: int, lots: int, capital_used: float):
        """Execute a trading signal."""
        symbol = signal.symbol
        
        print(f"\n🎯 {signal.trade_type.value} on {symbol}")
        print(f"   Type: {signal.signal_type.value}")
        print(f"   Direction: {signal.direction.value}")
        print(f"   Entry: ₹{signal.entry_price:.2f}")
        print(f"   Stop: ₹{signal.stop_loss:.2f}")
        print(f"   Target: ₹{signal.take_profit:.2f}")
        
        # Use calculated Sizing
        # lots = strategy.calculate_lot_size(self.capital, signal.entry_price, signal.stop_loss)
        # lot_size = 50 if symbol == "NIFTY" else 25
        # qty = lots * lot_size
        
        self.positions[symbol] = {
            "entry": signal.entry_price,
            "qty": qty,
            "lots": lots,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "direction": signal.direction,
            "trade_type": signal.trade_type,
            "timestamp": signal.timestamp
        }
        
        strategy = self.strategies[symbol]
        strategy.trades_today += 1
        self.trades_today[symbol] += 1
        
        self.capital -= capital_used # Deduct used capital (margin lock) roughly? 
        # Actually in paper trading accounting, usually we just track balance.
        # But to be safe let's assume margin matches price for simplicity or keep balance intact and check available
        # The prompt says "Ignore total account balance beyond this limit" for sizing, but for accounting we should track properly.
        # Let's keep self.capital as "Available Balance" for simplicity in checking logic.
        
        print(f"   ✅ EXECUTED: {lots} lot(s) ({qty} units)")
    
    def check_exit(self, symbol: str, current_price: float = 0.0):
        """Check if position should exit."""
        pos = self.positions.get(symbol)
        if not pos:
            return
        
        current = current_price
        
        # If no LTP provided, fetch candle (fallback)
        if current <= 0:
            # Use '1m' -> '1minute' map
            df = get_candles(symbol, "1m", 1)
            if df.empty:
                return
            current = df['close'].iloc[-1]
        
        should_exit = False
        pnl = 0.0
        reason = ""
        
        # Calculate current floating PnL for dashboard display
        if pos["direction"] == Direction.LONG:
            floating_pnl = (current - pos["entry"]) * pos["qty"]
        else:
            floating_pnl = (pos["entry"] - current) * pos["qty"]
            
        # Store in position for dashboard
        pos['pnl'] = floating_pnl
        
        if pos["direction"] == Direction.LONG:
            if current <= pos["sl"]:
                should_exit = True
                reason = "STOP LOSS"
                pnl = floating_pnl
            elif current >= pos["tp"]:
                should_exit = True
                reason = "TAKE PROFIT"
                pnl = floating_pnl
        else:  # SHORT
            if current >= pos["sl"]:
                should_exit = True
                reason = "STOP LOSS"
                pnl = floating_pnl
            elif current <= pos["tp"]:
                should_exit = True
                reason = "TAKE PROFIT"
                pnl = floating_pnl
        
        if should_exit:
            self.close_position(symbol, pnl, reason)




    def check_mandatory_exits(self):
        """Check for mandatory 15:20 IST exit."""
        now = datetime.now(IST).time()
        
        if now >= dt.time(15, 20):
            for symbol in list(self.positions.keys()):
                # Use candle or LTP? Stick to candle for safety at end of day, or simple LTP
                # Let's use LTP for speed
                adapter = get_upstox_adapter()
                ltp_data = adapter.get_ltp(symbol)
                current = ltp_data.get("price", 0) if ltp_data else 0
                
                if current == 0:
                    continue

                pos = self.positions[symbol]
                
                if pos["direction"] == Direction.LONG:
                    pnl = (current - pos["entry"]) * pos["qty"]
                else:
                    pnl = (pos["entry"] - current) * pos["qty"]
                
                self.close_position(symbol, pnl, "TIME EXIT (15:20)")

    def close_position(self, symbol: str, pnl: float, reason: str):
        """Close a position and update P&L."""
        pos = self.positions[symbol]
        
        if symbol == "NIFTY":
            self.nifty_pnl += pnl
        else:
            self.banknifty_pnl += pnl
        
        self.total_pnl = self.nifty_pnl + self.banknifty_pnl
        self.capital += pnl
        
        if pnl > 0:
            self.wins[symbol] += 1
            print(f"✅ WIN [{symbol}]: {reason} | +₹{pnl:,.0f}")
        else:
            self.losses[symbol] += 1
            self.strategies[symbol].losses_today += 1
            # Cooldown: Skip next 2 signals
            self.strategies[symbol].activate_cooldown(2)
            print(f"❌ LOSS [{symbol}]: {reason} | ₹{pnl:,.0f} (Cooldown Activated)")
        
        del self.positions[symbol]
        self.update_dashboard()

    def update_dashboard(self):
        """Send update to dashboard."""
        try:
            payload = {
                "balance_indian": self.capital,
                "pnl_indian": self.total_pnl,
                "signal": "INDIAN_FO",
                "confidence": 90,
                "reasoning": f"NIFTY P&L: ₹{self.nifty_pnl:,.0f} | BANKNIFTY P&L: ₹{self.banknifty_pnl:,.0f}",
                "positions": {
                    sym: {
                        "symbol": sym,
                        "entry_price": p["entry"],
                        "quantity": p["qty"],
                        "side": p["direction"].value,
                        "sl": p["sl"],
                        "tp": p["tp"],
                        "trade_type": p["trade_type"].value,
                        "pnl": p.get("pnl", 0.0) # Send Live Floating PnL
                    } for sym, p in self.positions.items()
                }
            }
            # Less verbose logging for high frequency
            print(f"   📡 Sending Dashboard Update: {len(payload['positions'])} positions")
            resp = requests.post(DASHBOARD_URL, json=payload, timeout=2)
            if resp.status_code != 200:
                print(f"   ❌ Dashboard Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"   ❌ Update Failed: {e}")

    def print_status(self):
        """Print current status."""
        print(f"\n💼 Capital: ₹{self.capital:,.0f} | Total P&L: ₹{self.total_pnl:+,.0f}")
        print(f"   NIFTY: {self.trades_today['NIFTY']} trades | P&L: ₹{self.nifty_pnl:+,.0f}")
        print(f"   BANKNIFTY: {self.trades_today['BANKNIFTY']} trades | P&L: ₹{self.banknifty_pnl:+,.0f}")
        
        if self.positions:
            for sym, p in self.positions.items():
                print(f"   📍 {sym} {p['direction'].value} @ ₹{p['entry']:.0f}")
        else:
            print("   ⚪ No positions")

    def check_manual_triggers(self):
        """Check for manual trigger files to force trades."""
        trigger_file = "TRIGGER_BUY_NIFTY"
        if os.path.exists(trigger_file):
            print("\n⚠️ MANUAL TRIGGER DETECTED: BUY NIFTY")
            try:
                os.remove(trigger_file)
                
                symbol = "NIFTY"
                adapter = get_upstox_adapter()
                ltp_data = adapter.get_ltp(symbol)
                # Key in store is 'price', not 'last_price'
                price = ltp_data.get("price", 0) if ltp_data else 0
                
                print(f"   🔍 Manual Trigger Price Fetch: {symbol} = {price}")

                if price == 0:
                     # Fallback to candle
                     # Use '1m' -> '1minute' to avoid API error
                     df = get_candles(symbol, "1m", 1) 
                     if not df.empty:
                         price = df['close'].iloc[-1]
                         print(f"   🔍 Manual Trigger Candle Fallback: {price}")
                
                if price > 0:
                    # Construct Manual Signal
                    signal = IndianFOSignal(
                        symbol=symbol,
                        signal_type=SignalType.FORCED_TRADE,
                        trade_type=TradeType.FORCED_DAILY,
                        direction=Direction.LONG,
                        entry_price=price,
                        stop_loss=price - 50,    # 50 pts SL
                        take_profit=price + 100, # 100 pts TP
                        breakout_level=price, # Not really breakout
                        instrument=InstrumentType.FUTURES, # Default
                        option_type="CALL",
                        timestamp=datetime.now(IST)
                    )
                    self.execute_signal(signal)
                    self.update_dashboard()
                else:
                    print(f"❌ Could not fetch price for manual trade.")
            except Exception as e:
                print(f"❌ Manual Trigger Error: {e}")

    def process_active_positions(self):
        """Update P&L and check exits for all active positions using LIVE feed."""
        if not self.positions:
            # Still update dashboard to show "0 positions" / heartbeat
            self.update_dashboard()
            return

        adapter = get_upstox_adapter()
        
        for symbol in list(self.positions.keys()):
            # Get Instant LTP from Memory Stream
            ltp_data = adapter.get_ltp(symbol)
            # Key in store is 'price'
            price = ltp_data.get("price", 0) if ltp_data else 0
            
            if price > 0:
                self.check_exit(symbol, current_price=price)
        
        # Send update
        self.update_dashboard()

    def run(self):
        """Main loop."""
        print(f"🚀 Trader Started. Monitoring {list(SYMBOLS.keys())}...")
        
        last_analysis_time = 0
        
        while True:
            try:
                # 1. Check Triggers (Highest Priority)
                self.check_manual_triggers()
                
                # 2. Process Live Positions (1Hz Checks)
                self.process_active_positions()
                
                # 3. Run Strategy Analysis (Every 60s)
                now_ts = time.time()
                if now_ts - last_analysis_time >= ANALYSIS_INTERVAL:
                    self.run_analysis()
                    last_analysis_time = now_ts
                
                # 4. Fast Loop Sleep
                time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Stopped")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    trader = IndianFOTrader()
    trader.run()


if __name__ == "__main__":
    main()
