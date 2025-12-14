import os
import time
import requests
from dotenv import load_dotenv
load_dotenv()
from quant_engine.strategy_spot import SpotStrategy
from quant_engine.strategy_futures import FuturesStrategy
from quant_engine.risk import RiskManager
from quant_engine.execution_futures import FuturesExecution
from quant_engine.execution_spot import SpotExecution
from quant_engine.config import SYMBOLS, TIMEFRAMES, TIMEFRAME_WEIGHTS, CONFIDENCE_THRESHOLD, LEVERAGE_MAP, COOLDOWN_CANDLES

# ============================================================================
# CONFIGURATION
# ============================================================================
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
BINANCE_SPOT_KEY = os.environ.get("BINANCE_SPOT_API_KEY", "")
BINANCE_SPOT_SECRET = os.environ.get("BINANCE_SPOT_API_SECRET", "")
DASHBOARD_URL = "http://localhost:8083/api/ai-decision"

class GenericBot:
    def __init__(self, mode, execution_cls, strategy_cls, api_key, api_secret):
        self.mode = mode
        self.exec = execution_cls(api_key, api_secret, testnet=True)
        self.strategy = strategy_cls
        
        # --- ACCOUNTING STATE ---
        self.realized_pnl = 0.0
        self.current_prices = {} 
        
        # --- STARTUP CHECK ---
        print(f"⌛ {mode}: waiting for exchange connection...")
        acct_data = None
        while acct_data is None:
            acct_data = self.exec.get_balance()
            if acct_data is None:
                time.sleep(1)
        
        print(f"✅ {mode} Connected. Wallet: ${acct_data['wallet_balance']:.2f}")

        # --- RISK MANAGER ---
        # Risk Manager uses Wallet Balance to determine sizing base
        self.risk = RiskManager(equity=acct_data['wallet_balance'], account_type=mode)
        
        self.positions = {} 
        self.kill_switch = False
        self.cooldowns = {s: 0 for s in SYMBOLS}
        
        if mode == "FUTURES":
            print(f"🛡️ {mode}: Setting Leverage...")
            for s in SYMBOLS:
                self.exec.set_leverage(s, LEVERAGE_MAP.get(s, 2))
                
            print(f"🔄 {mode}: Syncing active positions...")
            active_pos = self.exec.get_positions()
            for p in active_pos:
                sym = p['symbol']
                qty = abs(p['amount'])
                entry = p['entryPrice']
                side = "LONG" if p['amount'] > 0 else "SHORT"
                
                try:
                    df = self.exec.get_candles(sym, "15m", limit=50)
                    if not df.empty:
                        df = self.strategy.calculate_indicators(df)
                        last_atr = df.iloc[-1]['atr']
                        self.current_prices[sym] = df.iloc[-1]['close']
                        
                        if side == "LONG":
                             sl = entry - (0.5 * last_atr)
                             risk_dist = abs(entry - sl)
                             tp = entry + (1.5 * risk_dist)
                        else:
                             sl = entry + (0.5 * last_atr)
                             risk_dist = abs(entry - sl)
                             tp = entry - (1.5 * risk_dist)
                             
                        self.positions[sym] = {
                            "symbol": sym, "side": side, "entry_price": entry, 
                            "quantity": qty, "sl": sl, "tp": tp
                        }
                        print(f"✅ Restored {sym} {side} @ {entry}")
                except Exception as e:
                    print(f"⚠️ Failed to restore {sym} details: {e}")

    def run_cycle(self):
        if self.kill_switch: return

        # 1. FETCH EXACT ACCT DATA (Source of Truth)
        acct_data = self.exec.get_balance()
        if acct_data is None: return 
        
        # 2. UPDATE RISK MANAGER
        # We start fresh with current wallet balance every cycle to ensure sizing is based on reality
        self.risk.equity = acct_data['wallet_balance']
        
        # 3. REPORT TO DASHBOARD (The critical part)
        self.report_dashboard("Scanning", acct_data)

        # 4. MARKET ANALYSIS & EXECUTION
        self.analyze_market()

        # 5. SYNC POSITIONS (Source of Truth Reconciliation)
        # Every cycle ensures we don't hold "ghost" positions or miss real ones
        self.sync_positions()
            
        # HEARTBEAT LOG (Every ~10s)
        if int(time.time()) % 10 == 0:
            print(f"💓 {self.mode} Scanning... Balance: ${acct_data['wallet_balance']:.2f}")

    def analyze_market(self):
        """
        Multi-Timeframe Analysis Engine:
        1. Analyzes ALL symbols on ALL timeframes.
        2. Aggregates Confidence Scores.
        3. Executes BEST opportunity only.
        """
        # If max positions reached, manage existing ones only
        if len(self.positions) >= 1: 
            for symbol in list(self.positions.keys()):
                try:
                    df = self.exec.get_candles(symbol, "15m")
                    if not df.empty:
                        last = df.iloc[-1]
                        self.current_prices[symbol] = last['close']
                        self.manage_position(symbol, last['close'], last['rsi'])
                except Exception as e:
                    print(f"⚠️ Management Error {symbol}: {e}")
            return

        candidates = []
        rejected = []

        for symbol in SYMBOLS:
            if time.time() < self.cooldowns.get(symbol, 0): continue
            
            try:
                tf_results = {}
                direction = None
                valid_symbol = True
                
                # Check ALL timeframes
                for tf in TIMEFRAMES:
                    df = self.exec.get_candles(symbol, tf)
                    if df.empty: 
                        valid_symbol = False
                        break
                        
                    df = self.strategy.calculate_indicators(df)
                    supports, resistances = self.strategy.find_sr_zones(df)
                    signal, trigger, confidence = self.strategy.check_entry(symbol, df, supports, resistances)
                    
                    if tf == "15m":
                        self.current_prices[symbol] = df.iloc[-1]['close'] 
                    
                    tf_results[tf] = {"signal": signal, "confidence": confidence, "close": df.iloc[-1]['close'], "atr": df.iloc[-1]['atr']}
                    
                    if signal is None:
                        valid_symbol = False
                        break
                    if direction is None:
                        direction = signal
                    elif direction != signal:
                        valid_symbol = False
                        break
                
                if valid_symbol:
                    # Calculate Score
                    final_score = 0.0
                    for tf, weight in TIMEFRAME_WEIGHTS.items():
                        final_score += tf_results[tf]["confidence"] * weight
                    
                    if final_score >= CONFIDENCE_THRESHOLD:
                        candidates.append({
                            "symbol": symbol, "score": final_score, "direction": direction,
                            "trigger_price": tf_results["5m"]["close"],
                            "atr": tf_results["15m"]["atr"]
                        })
                    else:
                        rejected.append(f"{symbol} {direction} ({final_score:.2f})")
                
            except Exception as e:
                print(f"⚠️ Analysis Error {symbol}: {e}")

        # Execution or Logging
        if candidates:
            best_setup = sorted(candidates, key=lambda x: x['score'], reverse=True)[0]
            print(f"🎯 Best Setup: {best_setup['symbol']} {best_setup['direction']} (Score: {best_setup['score']:.2f})")
            self.enter_trade(best_setup['symbol'], best_setup['direction'], best_setup['trigger_price'], best_setup['trigger_price'], best_setup['atr'])
        elif rejected:
            # If we had signals but low score
            print(f"🔎 Signals Found (Low Conf): {', '.join(rejected)} [Req: {CONFIDENCE_THRESHOLD}]")


    def sync_positions(self):
        """
        CRITICAL: Reconcile internal state with Exchange Reality.
        1. If Exchange has position but we don't -> Adopt it (Recovery).
        2. If We have position but Exchange doesn't -> Delete it (Confirmed Close).
        """
        try:
            # Spot doesn't really have "Positions" in the same way, but we can check non-dust balances if needed.
            # For Futures, this is critical.
            if self.mode == "FUTURES":
                exchange_positions = self.exec.get_positions() # Returns list of active pos dicts
                
                # Setup Maps for O(1) lookup
                exchange_map = {p['symbol']: p for p in exchange_positions if p['amount'] != 0}
                internal_map = self.positions
                
                # A. Check for Confirmed Closes (Internal YES, Exchange NO)
                symbols_to_remove = []
                for sym in internal_map:
                    if sym not in exchange_map:
                        symbols_to_remove.append(sym)
                
                for sym in symbols_to_remove:
                    print(f"✅ {self.mode} CONFIRMED CLOSE: {sym} removed from state.")
                    del self.positions[sym]
                    
                # B. Check for Ghosts/Recovery (Exchange YES, Internal NO)
                for sym, p in exchange_map.items():
                    if sym not in internal_map:
                        print(f"⚠️ {self.mode} RECOVERING POSITION: {sym} found on exchange but not in memory.")
                        # Re-construct basic state
                        side = "LONG" if p['amount'] > 0 else "SHORT"
                        # Recover TP/SL from logic or defaults (since we lost memory)
                        # For now, we set wide safety nets or rely on next cycle to manage it
                        self.positions[sym] = {
                            "symbol": sym, "side": side, "entry_price": p['entryPrice'],
                            "quantity": abs(p['amount']), "sl": 0, "tp": 0 # TODO: Smarter recovery?
                        }
                        
        except Exception as e:
            print(f"⚠️ Sync Error: {e}")

    def enter_trade(self, symbol, signal, price, trigger, atr):
        print(f"✨ {self.mode} {signal}: {symbol} @ ${price}")
        
        if signal == "LONG": sl = trigger - (0.5 * atr)
        else: sl = trigger + (0.5 * atr)
            
        qty = self.risk.calculate_position_size(symbol, price, sl)
        if (qty * price) < 10: 
            print(f"✋ {self.mode} Skip: Size too small")
            return

        print(f"🚀 {self.mode} EXEC: {signal} {qty} {symbol}")
        order_side = "BUY" if signal == "LONG" else "SELL"
        order = self.exec.place_order(symbol, order_side, qty)
        
        if order:
             risk_dist = abs(price - sl)
             tp = (price + 1.5*risk_dist) if signal == "LONG" else (price - 1.5*risk_dist)
             self.positions[symbol] = {"symbol": symbol, "side": signal, "entry_price": price, "quantity": qty, "sl": sl, "tp": tp}

    def manage_position(self, symbol, price, rsi):
        pos = self.positions[symbol]
        side = pos['side']
        exit_r = None
        
        if side == "LONG" and price <= pos['sl']: exit_r = "Stop Loss"
        if side == "SHORT" and price >= pos['sl']: exit_r = "Stop Loss"
        if side == "LONG" and price >= pos['tp']: exit_r = "Take Profit"
        if side == "SHORT" and price <= pos['tp']: exit_r = "Take Profit"
        if side == "SHORT" and rsi < 30: exit_r = "RSI Min"

        if exit_r:
            print(f"📉 {self.mode} CLOSING {symbol}: {exit_r}")
            close_side = "SELL" if side == "LONG" else "BUY"
            
            if self.mode == "FUTURES":
                self.exec.place_order(symbol, close_side, pos['quantity'], reduce_only=True)
            else:
                self.exec.place_order(symbol, close_side, pos['quantity'])
                
            entry = pos['entry_price']
            qty = pos['quantity']
            
            trade_pnl = (price - entry) * qty if side == "LONG" else (entry - price) * qty
            self.realized_pnl += trade_pnl
            print(f"💰 PnL Stored: ${trade_pnl:.2f} (Total Realized: ${self.realized_pnl:.2f})")
                
            # DO NOT DELETE POSITION HERE. 
            # We wait for sync_positions() to confirm it is gone from the exchange.
            # This prevents "Optimistic State Deletion" bugs.
            print(f"⏳ {self.mode} Order Sent. Waiting for sync to confirm close...")
            
            # Cooldown is fine to set optimistically as we don't want to re-enter immediately anyway
            self.cooldowns[symbol] = time.time() + (COOLDOWN_CANDLES * 60)

    def report_dashboard(self, msg, acct_data):
        try:
             # UNREALIZED PnL CALC (Display Only)
             unrealized_pnl = 0.0
             
             # If Futures, utilize the API's unrealized pnl for accuracy if available?
             # User said: "Sum of PnL from OPEN futures positions".
             # The API gives `totalUnrealizedProfit` in `acct_data['unrealized_pnl']`.
             # We should use that for FUTURES as it's the source of truth.
             
             if self.mode == "FUTURES":
                 unrealized_pnl = acct_data.get('unrealized_pnl', 0.0)
             else:
                 # Spot doesn't have "unrealized PnL" in account obj typically, we calc manually
                 for sym, pos in self.positions.items():
                     current_price = self.current_prices.get(sym, pos['entry_price'])
                     qty = pos['quantity']
                     if pos['side'] == "LONG":
                         unrealized_pnl += (current_price - pos['entry_price']) * qty
                     else:
                         unrealized_pnl += (pos['entry_price'] - current_price) * qty
            
             total_display_pnl = self.realized_pnl + unrealized_pnl
             
             payload = {
                f"balance_{self.mode.lower()}": acct_data['wallet_balance'],
                f"pnl_{self.mode.lower()}": total_display_pnl,
                # Extra fields for strict compliance
                f"margin_{self.mode.lower()}": acct_data.get('margin_used', 0.0),
                f"available_{self.mode.lower()}": acct_data.get('available_balance', acct_data['wallet_balance']),
                
                "reasoning": f"{self.mode} Bot: {msg}",
                "positions": {k: {k2: float(v2) if hasattr(v2, 'item') else v2 for k2, v2 in v.items()} for k, v in self.positions.items()}
             }
             requests.post(DASHBOARD_URL, json=payload, timeout=0.5)
        except: pass


if __name__ == "__main__":
    print("🤖 HYBRID QUANT SYSTEM STARTING ( STRICT EXCHANGE SYNC )...")
    
    # Init with NO CAP. Pure Exchange Data.
    spot_bot = GenericBot("SPOT", SpotExecution, SpotStrategy, BINANCE_SPOT_KEY, BINANCE_SPOT_SECRET)
    futures_bot = GenericBot("FUTURES", FuturesExecution, FuturesStrategy, BINANCE_API_KEY, BINANCE_API_SECRET)
    
    print("✅ System Active. Scanning...")
    
    while True:
        try:
            spot_bot.run_cycle()
            futures_bot.run_cycle()
            time.sleep(1)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"FATAL: {e}")
            time.sleep(10)
