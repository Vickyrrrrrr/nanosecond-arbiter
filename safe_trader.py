
import os
import json
import time
import requests
import hmac
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

# ============================================================================
# CONFIGURATION
# ============================================================================

# Binance Testnet
BINANCE_BASE_URL = 'https://testnet.binance.vision/api/v3'
API_KEY = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Risk Management
MAX_CAPITAL = 10000.0
RISK_PER_TRADE_PERCENT = 0.01  # 1%
STOP_LOSS_PERCENT = 0.015      # 1.5%
TAKE_PROFIT_PERCENT = 0.025    # 2.5%
MAX_TRADES_PER_DAY = 5

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DASHBOARD_URL = "http://localhost:8083/api/ai-decision"

# ============================================================================
# BINANCE INTERFACE
# ============================================================================

def get_signature(params):
    query_string = urlencode(params)
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_candles(symbol: str, interval: str, limit: int = 20) -> List[Dict]:
    """Fetch candlestick data"""
    try:
        url = f"{BINANCE_BASE_URL}/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        response = requests.get(url, params=params)
        data = response.json()
        
        # Parse [Open time, Open, High, Low, Close, Volume, ...]
        candles = []
        for c in data:
            candles.append({
                "time": datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M'),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5])
            })
        return candles
    except Exception as e:
        print(f"⚠️ Error fetching {interval} candles for {symbol}: {e}")
        return []

def get_account_balance():
    """Get USDT balance"""
    try:
        if not API_KEY: return 10000.0 # Fallback for testing
        
        headers = {'X-MBX-APIKEY': API_KEY}
        params = {'timestamp': int(time.time() * 1000)}
        params['signature'] = get_signature(params)
        
        response = requests.get(f"{BINANCE_BASE_URL}/account", params=params, headers=headers)
        if response.status_code == 200:
            balances = response.json()['balances']
            for b in balances:
                if b['asset'] == 'USDT':
                    return float(b['free'])
        return 0.0
    except:
        return 0.0

def place_order(symbol: str, side: str, quantity: float):
    """Place market order"""
    if not API_KEY: return None
    
    try:
        headers = {'X-MBX-APIKEY': API_KEY}
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        params['signature'] = get_signature(params)
        
        response = requests.post(f"{BINANCE_BASE_URL}/order", params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Order failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Execution error: {e}")
        return None

# ============================================================================
# AI TRADER CLASS
# ============================================================================

class SafeTrader:
    def __init__(self):
        self.positions = {} # {symbol: {entry_price, quantity, sl, tp}}
        self.daily_trades = 0
        self.balance = 0.0
        self.start_balance = None # Lazy load on first successful fetch
        self.total_pnl = 0.0
        
    def analyze_market_and_decide(self):
        """Main analysis loop"""
        
        # 1. Gather Data
        market_data = {}
        for symbol in SYMBOLS:
            market_data[symbol] = {
                "1h": get_candles(symbol, "1h", 10),
                "4h": get_candles(symbol, "4h", 10),
                "1d": get_candles(symbol, "1d", 10)
            }
        
        # Update current balance
        current_bal = get_account_balance()
        if current_bal > 0:
            self.balance = current_bal
            
            # Set start balance if not set yet (fixes startup race condition)
            if self.start_balance is None:
                self.start_balance = self.balance
                print(f"💰 Session Start Balance: ${self.start_balance:.2f}")
            
            self.total_pnl = self.balance - self.start_balance

        # 2. Send Heartbeat to Dashboard (Ensure Balance Updates)
        self.update_dashboard({"analysis": "Analyzing market data (Waiting for AI)..."})
        
        # 3. Construct Prompt
        prompt = self.create_prompt(market_data)
        
        # 3. Get AI Decision
        decision = self.call_gemini(prompt)
        if not decision: return
        
        # 4. Report Decisions
        self.print_portfolio(decision)
        self.update_dashboard(decision)
        
        # 5. Execute Trades
        self.execute_decision(decision)

    def create_prompt(self, market_data):
        return f"""
You are an AI trading analyst integrated inside a high-frequency trading engine. 
Your goal is to trade SAFELY and PROFITABLY using a maximum capital of $10,000.

Your priorities:
1. CAPITAL PRESERVATION
2. LOW-RISK ENTRIES ONLY
3. STRICT STOP-LOSS AND TAKE-PROFIT
4. NO OVERTRADING

==========================
MARKET DATA
==========================
Capital Available: ${self.balance:.2f}
Active Positions: {json.dumps(self.positions)}
Market Data (1h, 4h, 1d K-Lines):
{json.dumps(market_data, indent=2)}

==========================
TRADING RULES
==========================
For every trade:
• Risk per trade: 1–2% max ({RISK_PER_TRADE_PERCENT*100}%)
• Stop-loss: -1% to -2%
• Take-profit: +2% to +3%

Enter a trade ONLY when:
• Price cleanly breaks a strong support/resistance level AND
• Retests that level OR shows strong continuation AND
• Trend, volume, and momentum agree with direction
• Confidence is HIGH (>80%)

Exit trade IMMEDIATELY if:
• Profit reaches 2–3%
• Loss reaches 1–2%
• Trend weakens or invalidates the setup

NO SCALPING unless a breakout is extremely clear.
NO revenge-trading.
NO entering trades during volatile news spikes.

==========================
BEHAVIOR RULES
==========================
• NEVER open random trades
• NEVER trade without technical confirmation
• ALWAYS protect capital first, profit second
• ALWAYS follow stop-loss and take-profit rules
• KEEP trading frequency low but high quality

==========================
RESPONSE FORMAT (JSON ONLY)
==========================
{{
    "analysis": "Explain in 3–4 short sentences: What trend observed, what S/R level triggered, why high confidence.",
    "trade_signal": {{
        "symbol": "BTCUSDT/ETHUSDT/SOLUSDT" or null,
        "action": "BUY" or "SELL" or "HOLD",
        "confidence": 0-100,
        "reason": "Brief reason"
    }}
}}
"""

    def call_gemini(self, prompt, model="gemini-2.0-flash"):
        print(f"DEBUG: Calling {model}... Key present: {bool(GEMINI_API_KEY)}")
        if not GEMINI_API_KEY:
            print("⚠️ Missing GEMINI_API_KEY")
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            print(f"DEBUG: Gemini Status: {resp.status_code}")
            
            if resp.status_code == 429:
                print("⚠️ Rate limit hit. Waiting 120s...")
                time.sleep(120)
                return self.call_gemini(prompt, model)
                
            if resp.status_code != 200:
                print(f"DEBUG: Gemini Error: {resp.text}")
            
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception as e:
            print(f"⚠️ AI Error: {e}")
        return None

    def execute_decision(self, decision):
        signal = decision.get("trade_signal")
        if not signal or signal["action"] == "HOLD": return
        
        symbol = signal["symbol"]
        action = signal["action"]
        confidence = signal.get("confidence", 0)
        
        print(f"🧠 Signal: {action} {symbol} ({confidence}%) - {signal.get('reason')}")
        
        if confidence < 80:
            print(f"✋ Skipping {symbol} {action} - Confidence {confidence}% too low.")
            return

        current_price = get_candles(symbol, "1m", 1)[-1]["close"]
        
        if action == "BUY" and symbol not in self.positions:
            # Calculate Risk Position Size
            risk_amount = self.balance * RISK_PER_TRADE_PERCENT
            sl_price = current_price * (1 - STOP_LOSS_PERCENT)
            shares = risk_amount / (current_price - sl_price) # Risk based sizing
            
            # Cap size at 10% of capital to be safe
            max_shares = (self.balance * 0.10) / current_price
            shares = min(shares, max_shares)
            
            # Execute
            print(f"🚀 EXECUTING BUY: {shares:.4f} {symbol} @ ${current_price}")
            order = place_order(symbol, "BUY", shares)
            
            if order or not API_KEY: # Sim success if no API key
                self.positions[symbol] = {
                    "entry": current_price,
                    "qty": shares,
                    "sl": sl_price,
                    "tp": current_price * (1 + TAKE_PROFIT_PERCENT)
                }
                self.daily_trades += 1
                
        elif action == "SELL" and symbol in self.positions:
            pos = self.positions[symbol]
            shares = pos["qty"]
            print(f"🔻 EXECUTING SELL: {shares:.4f} {symbol} @ ${current_price}")
            place_order(symbol, "SELL", shares)
            
            # PnL logic
            pnl = (current_price - pos["entry"]) * shares
            self.total_pnl += pnl
            del self.positions[symbol]
            
    def print_portfolio(self, decision):
        print("\n" + "="*50)
        print("🤖 AI SAFE TRADER PORTFOLIO")
        print("="*50)
        print(f"💰 Capital: ${self.balance:,.2f}")
        print(f"📈 Total P&L: ${self.total_pnl:+.2f}")
        print(f"📊 Trades Today: {self.daily_trades}")
        print("-" * 50)
        
        if self.positions:
            for sym, pos in self.positions.items():
                curr = get_candles(sym, "1m", 1)[-1]["close"]
                pnl = (curr - pos["entry"]) * pos["qty"]
                pnl_pct = (pnl / (pos["entry"]*pos["qty"])) * 100
                print(f"🟢 {sym}: {pos['qty']:.4f} units | Entry: ${pos['entry']:.2f}")
                print(f"   Current: ${curr:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        else:
            print("⚪ No Active Positions")
            
        print("-" * 50)
        print(f"🧠 Analysis: {decision.get('analysis', '')[:200]}...")
        print("="*50 + "\n")

    def update_dashboard(self, decision):
        try:
            # Simulate a fresh $10k start for the user
            # Real Balance is self.balance, but we report 10000 + Session PnL
            display_balance = 10000.0 + self.total_pnl
            print(f"DEBUG: Pushing to Dashboard: Balance=${display_balance}")
            
            payload = {
                "balance": display_balance,
                "pnl": self.total_pnl,
                "positions": {
                    s: {
                        "entry_price": p["entry"], 
                        "quantity": p["qty"], 
                        "current_price": p["entry"], # update ideally
                        "pnl": 0,
                        "capital": p["entry"]*p["qty"]
                    } for s, p in self.positions.items()
                },
                "reasoning": decision.get("analysis", "")
            }
            requests.post(DASHBOARD_URL, json=payload, timeout=1)
        except: pass

def main():
    trader = SafeTrader()
    print("🛡️ SAFE TRADER INITIALIZED")
    print("waiting for market data...")
    
    while True:
        try:
            trader.analyze_market_and_decide()
            print("⏳ Cooldown 120s...")
            time.sleep(120)
        except KeyboardInterrupt:
            print("🛑 Stopping...")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
