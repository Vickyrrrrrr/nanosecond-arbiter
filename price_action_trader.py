"""
Trend Momentum Volatility Trader Bot
=====================================
Main trading bot implementing Trend Momentum Volatility Strategy.

Uses EMA (50/100/200), RSI (14), ATR (14), Volume (20)

Usage:
    python price_action_trader.py [--mode spot|futures]
"""

import os
import sys
import json
import time
import hmac
import hashlib
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_engine.strategy_trend_momentum import (
    TrendMomentumVolatilityStrategy,
    MarketType,
    Direction,
    SignalType,
    TradeSignal,
    STRATEGY_NAME,
    RISK_PER_TRADE,
    SL_ATR_MULTIPLIER,
    TP_ATR_MULTIPLIER,
    BREAKEVEN_ATR,
    TRAIL_ATR
)

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

BINANCE_BASE_URL = "https://testnet.binance.vision/api/v3"
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

DASHBOARD_URL = "http://localhost:8083/api/ai-decision"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ANALYSIS_INTERVAL = 60  # Recalculate every 60 seconds

STARTING_CAPITAL = 5000.0  # $5,000 for spot mode


# ============================================================================
# BINANCE API
# ============================================================================

def get_signature(params: Dict) -> str:
    query_string = urlencode(params)
    return hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def get_candles(symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
    """Fetch candlestick data. Need 250 for EMA 200."""
    try:
        url = f"{BINANCE_BASE_URL}/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return pd.DataFrame()
        
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"⚠️ Error fetching candles: {e}")
        return pd.DataFrame()


def get_balance() -> float:
    """Get USDT balance."""
    try:
        if not API_KEY:
            return STARTING_CAPITAL
        
        headers = {'X-MBX-APIKEY': API_KEY}
        params = {'timestamp': int(time.time() * 1000)}
        params['signature'] = get_signature(params)
        
        response = requests.get(f"{BINANCE_BASE_URL}/account", params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            for b in response.json().get('balances', []):
                if b['asset'] == 'USDT':
                    return float(b['free'])
        return STARTING_CAPITAL
    except:
        return STARTING_CAPITAL


def place_order(symbol: str, side: str, quantity: float) -> Optional[Dict]:
    """Place market order."""
    if not API_KEY:
        print(f"📝 PAPER: {side} {quantity:.6f} {symbol}")
        return {"status": "FILLED", "paper": True}
    
    try:
        headers = {'X-MBX-APIKEY': API_KEY}
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': f"{quantity:.6f}",
            'timestamp': int(time.time() * 1000)
        }
        params['signature'] = get_signature(params)
        
        response = requests.post(f"{BINANCE_BASE_URL}/order", params=params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None


# ============================================================================
# TRADER BOT
# ============================================================================

class TrendMomentumTrader:
    """
    Trend Momentum Volatility Trading Bot.
    
    - Uses EMA 50/100/200 for trend
    - RSI 14 for momentum
    - ATR 14 for volatility-based SL/TP
    - Volume confirmation
    """
    
    def __init__(self, market_type: MarketType = MarketType.SPOT):
        self.market_type = market_type
        
        # Initialize strategies for each symbol
        self.strategies = {
            sym: TrendMomentumVolatilityStrategy(sym, market_type) for sym in SYMBOLS
        }
        
        # Portfolio
        self.balance = STARTING_CAPITAL
        self.start_balance = STARTING_CAPITAL
        self.total_pnl = 0.0
        self.positions: Dict[str, Dict] = {}
        self.trades = 0
        self.wins = 0
        self.losses = 0
        
        print(f"\n{'='*60}")
        print(f"⚡ {STRATEGY_NAME} TRADER")
        print(f"{'='*60}")
        print(f"Mode: {market_type.value}")
        print(f"Symbols: {', '.join(SYMBOLS)}")
        print(f"Capital: ${self.balance:,.2f}")
        print(f"Risk Per Trade: {RISK_PER_TRADE * 100}%")
        print(f"SL: {SL_ATR_MULTIPLIER}x ATR | TP: {TP_ATR_MULTIPLIER}x ATR")
        print(f"Breakeven: {BREAKEVEN_ATR}x ATR | Trail: {TRAIL_ATR}x ATR")
        print(f"Interval: {ANALYSIS_INTERVAL}s")
        print(f"{'='*60}\n")
    
    def fetch_data(self, symbol: str) -> pd.DataFrame:
        """Fetch 5m data for a symbol (need 250 candles for EMA 200)."""
        return get_candles(symbol, "5m", 250)
    
    def run_analysis(self):
        """Run analysis cycle."""
        now = datetime.now().strftime('%H:%M:%S')
        print(f"\n{'─'*60}")
        print(f"📊 ANALYSIS @ {now}")
        print(f"{'─'*60}")
        
        # Update balance
        self.balance = get_balance()
        self.total_pnl = self.balance - self.start_balance
        
        # Check exits first
        self.check_exits()
        
        # Look for new signals
        for symbol in SYMBOLS:
            if symbol in self.positions:
                continue
            
            data = self.fetch_data(symbol)
            if data.empty or len(data) < 210:
                print(f"   ⚪ {symbol}: Not enough data")
                continue
            
            strategy = self.strategies[symbol]
            signal = strategy.generate_signal(
                data,
                account_balance=self.balance,
                timestamp=int(time.time() * 1000)
            )
            
            if signal:
                self.execute_signal(signal)
        
        # Update dashboard
        self.update_dashboard()
        
        # Print status
        self.print_status()
    
    def execute_signal(self, signal: TradeSignal):
        """Execute a trade signal."""
        print(f"\n🎯 {signal.signal_type.value} on {signal.symbol}")
        print(f"   Entry: ${signal.entry_price:.2f}")
        print(f"   Stop: ${signal.stop_loss:.2f}")
        print(f"   Target: ${signal.take_profit:.2f}")
        print(f"   RSI: {signal.rsi:.1f} | ATR: ${signal.atr:.2f}")
        print(f"   Volume: {signal.volume_ratio:.1f}x avg")
        
        size = signal.position_size
        
        if size <= 0:
            print("   ❌ Size too small")
            return
        
        # Check Daily Limits
        today_str = datetime.now().strftime('%Y-%m-%d')
        if not hasattr(self, 'daily_trades'):
             self.daily_trades = {}
        
        daily_key = f"{today_str}|{signal.symbol}"
        count = self.daily_trades.get(daily_key, 0)
        
        if count >= 3:
            print(f"   🚫 Daily Limit Reached for {signal.symbol} ({count}/3)")
            return

        # Execute
        side = "BUY" if signal.direction == Direction.LONG else "SELL"
        order = place_order(signal.symbol, side, size)
        
        if order:
            self.positions[signal.symbol] = {
                "entry": signal.entry_price,
                "qty": size,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "direction": signal.direction,
                "atr": signal.atr,
                "breakeven_hit": False
            }
            self.trades += 1
            
            # Increment Daily Count
            self.daily_trades[daily_key] = count + 1
            
            print(f"   ✅ EXECUTED: {side} {size:.6f}")
    
    def check_exits(self):
        """Check positions for exit conditions with trailing stop logic."""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            
            # Get current price and ATR
            data = self.fetch_data(symbol)
            if data.empty:
                continue
            
            current = data['close'].iloc[-1]
            strategy = self.strategies[symbol]
            current_atr = strategy.calculate_atr(data).iloc[-1]
            
            should_exit = False
            pnl = 0.0
            reason = ""
            
            # Update trailing stop
            if pos["direction"] == Direction.LONG:
                # Check breakeven
                breakeven_level = pos["entry"] + (pos["atr"] * BREAKEVEN_ATR)
                if not pos["breakeven_hit"] and current >= breakeven_level:
                    pos["sl"] = pos["entry"]
                    pos["breakeven_hit"] = True
                    print(f"   🔒 {symbol} LONG: Breakeven activated")
                
                # Trailing stop
                trail_stop = current - (current_atr * TRAIL_ATR)
                pos["sl"] = max(pos["sl"], trail_stop)
                
                # Check exit
                if current <= pos["sl"]:
                    should_exit = True
                    reason = "STOP LOSS"
                    pnl = (current - pos["entry"]) * pos["qty"]
                elif current >= pos["tp"]:
                    should_exit = True
                    reason = "TAKE PROFIT"
                    pnl = (current - pos["entry"]) * pos["qty"]
            
            else:  # SHORT
                # Check breakeven
                breakeven_level = pos["entry"] - (pos["atr"] * BREAKEVEN_ATR)
                if not pos["breakeven_hit"] and current <= breakeven_level:
                    pos["sl"] = pos["entry"]
                    pos["breakeven_hit"] = True
                    print(f"   🔒 {symbol} SHORT: Breakeven activated")
                
                # Trailing stop
                trail_stop = current + (current_atr * TRAIL_ATR)
                pos["sl"] = min(pos["sl"], trail_stop)
                
                # Check exit
                if current >= pos["sl"]:
                    should_exit = True
                    reason = "STOP LOSS"
                    pnl = (pos["entry"] - current) * pos["qty"]
                elif current <= pos["tp"]:
                    should_exit = True
                    reason = "TAKE PROFIT"
                    pnl = (pos["entry"] - current) * pos["qty"]
            
            if should_exit:
                side = "SELL" if pos["direction"] == Direction.LONG else "BUY"
                place_order(symbol, side, pos["qty"])
                
                self.total_pnl += pnl
                
                if pnl > 0:
                    self.wins += 1
                    print(f"✅ WIN: {reason} {symbol} +${pnl:.2f}")
                else:
                    self.losses += 1
                    print(f"❌ LOSS: {reason} {symbol} ${pnl:.2f}")
                
                del self.positions[symbol]
    
    def update_dashboard(self):
        """Send update to dashboard."""
        try:
            payload = {
                "balance_spot": self.balance,
                "pnl_spot": self.total_pnl,
                "signal": STRATEGY_NAME,
                "confidence": 90,
                "reasoning": f"Trend Momentum Volatility | {self.market_type.value}",
                "positions": {
                    sym: {
                        "symbol": sym,
                        "entry_price": p["entry"],
                        "quantity": p["qty"],
                        "side": p["direction"].value,
                        "sl": p["sl"],
                        "tp": p["tp"]
                    } for sym, p in self.positions.items()
                }
            }
            requests.post(DASHBOARD_URL, json=payload, timeout=1)
        except:
            pass
    
    def print_status(self):
        """Print portfolio status."""
        print(f"\n💼 Balance: ${self.balance:,.2f} | P&L: ${self.total_pnl:+,.2f}")
        print(f"   Trades: {self.trades} | W/L: {self.wins}/{self.losses}")
        
        if self.positions:
            for sym, p in self.positions.items():
                print(f"   📍 {sym} {p['direction'].value} @ ${p['entry']:.2f} (SL: ${p['sl']:.2f})")
        else:
            print("   ⚪ No positions")
        
        print(f"\n⏳ Next analysis in {ANALYSIS_INTERVAL}s...")
    
    def run(self):
        """Main loop."""
        while True:
            try:
                self.run_analysis()
                time.sleep(ANALYSIS_INTERVAL)
            except KeyboardInterrupt:
                print("\n🛑 Stopped")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(10)


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Trend Momentum Volatility Trader")
    parser.add_argument("--mode", choices=["spot", "futures"], default="spot")
    args = parser.parse_args()
    
    market_type = MarketType.SPOT if args.mode == "spot" else MarketType.FUTURES
    
    trader = TrendMomentumTrader(market_type)
    trader.run()


if __name__ == "__main__":
    main()
