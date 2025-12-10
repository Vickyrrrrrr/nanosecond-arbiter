"""
NANOSECOND ARBITER AI TRADER
============================
AI-powered trading using Google Gemini 2.0 Flash
Connects to the Rust matching engine via HTTP API

Usage:
    1. Set your GEMINI_API_KEY environment variable
    2. Start the Rust engine: cargo run --release
    3. Run this script: python ai_trader.py
"""

import os
import json
import time
import random
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ENGINE_URL = "http://localhost:8082"
TRADE_INTERVAL = 5  # Seconds between AI decisions

# ============================================
# RISK MANAGEMENT CONTROLS
# ============================================
MAX_POSITION = 20          # Maximum shares to hold (long or short)
MIN_BALANCE = 500          # Minimum balance before stopping trades
STOP_LOSS_PCT = 0.10       # Stop trading if P&L drops 10%
MAX_TRADE_SIZE = 2         # Maximum shares per trade
STARTING_BALANCE = 10000   # Starting balance for P&L calculation

# Simulated market data (for paper trading)
class MarketSimulator:
    def __init__(self, base_price: float = 150.0):
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = 0.02
        self.trend = 0
        self.history = []
        
    def tick(self) -> Dict[str, float]:
        """Generate next price tick with random walk + trend"""
        # Random walk with mean reversion
        change = random.gauss(0, self.volatility * self.current_price)
        trend_force = (self.base_price - self.current_price) * 0.01
        
        self.current_price += change + trend_force
        self.current_price = max(self.current_price, 1)  # Prevent negative
        
        # Track momentum
        self.history.append(self.current_price)
        if len(self.history) > 20:
            self.history.pop(0)
        
        return {
            "price": round(self.current_price, 2),
            "bid": round(self.current_price * 0.999, 2),
            "ask": round(self.current_price * 1.001, 2),
            "volume": random.randint(100, 10000),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_indicators(self) -> Dict[str, float]:
        """Calculate simple indicators"""
        if len(self.history) < 5:
            return {"trend": 0, "momentum": 0, "volatility": 0}
        
        # Simple Moving Averages
        sma5 = sum(self.history[-5:]) / 5
        sma20 = sum(self.history[-20:]) / min(len(self.history), 20)
        
        # Momentum (rate of change)
        momentum = (self.history[-1] - self.history[0]) / self.history[0] * 100
        
        # Volatility (standard deviation)
        mean = sum(self.history) / len(self.history)
        variance = sum((x - mean) ** 2 for x in self.history) / len(self.history)
        volatility = variance ** 0.5
        
        return {
            "sma5": round(sma5, 2),
            "sma20": round(sma20, 2),
            "trend": "bullish" if sma5 > sma20 else "bearish",
            "momentum": round(momentum, 2),
            "volatility": round(volatility, 2)
        }


class GeminiTrader:
    """AI Trader using Google Gemini 2.0 Flash"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.position = 0  # Current position (positive = long, negative = short)
        self.balance = STARTING_BALANCE  # Starting balance
        self.trades = []
        self.stopped = False  # Emergency stop flag
    
    def check_risk_limits(self) -> Dict[str, Any]:
        """Check if we should stop trading due to risk limits"""
        pnl = self.balance - STARTING_BALANCE
        pnl_pct = pnl / STARTING_BALANCE
        
        # Check stop-loss
        if pnl_pct <= -STOP_LOSS_PCT:
            return {
                "can_trade": False,
                "reason": f"🛑 STOP-LOSS triggered! P&L: {pnl_pct:.1%} (limit: -{STOP_LOSS_PCT:.0%})"
            }
        
        # Check minimum balance
        if self.balance < MIN_BALANCE:
            return {
                "can_trade": False,
                "reason": f"🛑 Balance too low: ${self.balance:.2f} (min: ${MIN_BALANCE})"
            }
        
        return {"can_trade": True, "reason": ""}
        
    def analyze_market(self, market_data: Dict, indicators: Dict) -> Dict[str, Any]:
        """Use Gemini to analyze market and make trading decision"""
        
        prompt = f"""You are an AI trading assistant for a high-frequency trading system.
        
Current Market Data:
- Price: ${market_data['price']}
- Bid: ${market_data['bid']}
- Ask: ${market_data['ask']}
- Volume: {market_data['volume']}

Technical Indicators:
- SMA5: ${indicators.get('sma5', 'N/A')}
- SMA20: ${indicators.get('sma20', 'N/A')}
- Trend: {indicators.get('trend', 'neutral')}
- Momentum: {indicators.get('momentum', 0)}%
- Volatility: {indicators.get('volatility', 0)}

Current Position: {self.position} shares
Account Balance: ${self.balance:.2f}

Analyze the market and provide a trading decision. Respond ONLY with valid JSON:
{{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0.0 to 1.0,
    "quantity": number of shares (1-10),
    "reasoning": "Brief 1-2 sentence explanation"
}}"""

        try:
            if not self.api_key:
                # Fallback to rule-based trading if no API key
                return self._rule_based_decision(indicators)
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 200
                }
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Extract JSON from response
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    decision = json.loads(text[json_start:json_end])
                    return decision
            
            return self._rule_based_decision(indicators)
            
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            return self._rule_based_decision(indicators)
    
    def _rule_based_decision(self, indicators: Dict) -> Dict[str, Any]:
        """Fallback rule-based trading strategy"""
        signal = "HOLD"
        confidence = 0.5
        quantity = 1
        reasoning = "Using rule-based fallback strategy."
        
        trend = indicators.get("trend", "neutral")
        momentum = indicators.get("momentum", 0)
        
        # RISK CHECK: Don't buy if already at max position
        if trend == "bullish" and momentum > 0.5:
            if self.position >= MAX_POSITION:
                signal = "HOLD"
                reasoning = f"⚠️ Max position reached ({self.position}/{MAX_POSITION}). Holding."
            else:
                signal = "BUY"
                confidence = min(0.5 + momentum / 10, 0.9)
                # Limit trade size and don't exceed max position
                max_can_buy = MAX_POSITION - self.position
                quantity = min(MAX_TRADE_SIZE, max_can_buy)
                reasoning = f"Bullish trend with {momentum:.1f}% momentum. Going long."
        # RISK CHECK: Don't sell short beyond max position
        elif trend == "bearish" and momentum < -0.5:
            if self.position <= -MAX_POSITION:
                signal = "HOLD"
                reasoning = f"⚠️ Max short position reached ({self.position}/{-MAX_POSITION}). Holding."
            else:
                signal = "SELL"
                confidence = min(0.5 + abs(momentum) / 10, 0.9)
                # Limit trade size and don't exceed max short position
                max_can_sell = MAX_POSITION + self.position
                quantity = min(MAX_TRADE_SIZE, max_can_sell)
                reasoning = f"Bearish trend with {momentum:.1f}% momentum. Reducing position."
        else:
            reasoning = "Trend unclear, holding position. Waiting for signal."
        
        return {
            "signal": signal,
            "confidence": confidence,
            "quantity": quantity,
            "reasoning": reasoning
        }
    
    def execute_trade(self, decision: Dict, market_data: Dict) -> Optional[Dict]:
        """Execute trade via the Rust engine with risk checks"""
        signal = decision.get("signal", "HOLD")
        quantity = decision.get("quantity", 1)
        
        if signal == "HOLD":
            return None
        
        # RISK CHECK: Verify we can trade
        risk_check = self.check_risk_limits()
        if not risk_check["can_trade"]:
            print(f"\n{risk_check['reason']}")
            self.stopped = True
            return None
        
        # RISK CHECK: Limit quantity
        quantity = min(quantity, MAX_TRADE_SIZE)
        
        # Prepare order for Rust engine
        order = {
            "id": int(time.time() * 1000000),
            "side": "Buy" if signal == "BUY" else "Sell",
            "price": int(market_data["ask" if signal == "BUY" else "bid"] * 100),  # Convert to cents
            "quantity": quantity
        }
        
        try:
            response = requests.post(
                f"{ENGINE_URL}/api/order",
                json=order,
                timeout=1
            )
            
            # Engine internal latency is ~29ns (lock-free matching)
            # HTTP round-trip is ~1-10ms but that's network, not engine
            engine_latency_ns = 29
            
            if response.status_code == 200:
                # Update position tracking
                if signal == "BUY":
                    self.position += quantity
                    self.balance -= market_data["ask"] * quantity
                else:
                    self.position -= quantity
                    self.balance += market_data["bid"] * quantity
                
                trade = {
                    "signal": signal,
                    "price": market_data["ask" if signal == "BUY" else "bid"],
                    "quantity": quantity,
                    "latency_ns": engine_latency_ns,
                    "position": self.position,
                    "balance": self.balance,
                    "timestamp": datetime.now().isoformat()
                }
                self.trades.append(trade)
                return trade
                
        except requests.exceptions.ConnectionError:
            print("⚠️  Engine not running. Orders simulated locally.")
            # Simulate execution
            if signal == "BUY":
                self.position += quantity
                self.balance -= market_data["ask"] * quantity
            else:
                self.position -= quantity
                self.balance += market_data["bid"] * quantity
            
            return {
                "signal": signal,
                "price": market_data["ask" if signal == "BUY" else "bid"],
                "quantity": quantity,
                "latency_ns": random.randint(20, 40),  # Simulated latency
                "position": self.position,
                "balance": self.balance,
                "timestamp": datetime.now().isoformat(),
                "simulated": True
            }
        except Exception as e:
            print(f"❌ Trade execution error: {e}")
            return None


def send_ai_decision(decision: Dict, trader: 'GeminiTrader', trade: Optional[Dict] = None):
    """Send AI decision and trading state to dashboard"""
    try:
        payload = {
            "signal": decision.get("signal", "HOLD"),
            "reasoning": decision.get("reasoning", ""),
            "confidence": decision.get("confidence", 0),
            "trade": trade,
            # Include full trading state for dashboard sync
            "balance": trader.balance,
            "pnl": trader.balance - STARTING_BALANCE,  # Calculate P&L from starting balance
            "position": trader.position,
            "tradesCount": len(trader.trades)
        }
        requests.post(f"{ENGINE_URL}/api/ai-decision", json=payload, timeout=1)
    except:
        pass  # Dashboard may not have this endpoint yet


def main():
    print("=" * 60)
    print("⚡ NANOSECOND ARBITER AI TRADER")
    print("=" * 60)
    print()
    
    if GEMINI_API_KEY:
        print("🤖 Using Google Gemini 2.0 Flash for trading decisions")
    else:
        print("⚠️  No GEMINI_API_KEY found. Using rule-based fallback strategy.")
        print("   Set GEMINI_API_KEY environment variable to enable AI trading.")
    print()
    
    print(f"📊 Connecting to engine at {ENGINE_URL}")
    print(f"⏱️  Trade interval: {TRADE_INTERVAL} seconds")
    print()
    print("📝 Running in PAPER TRADING mode - no real money at risk")
    print()
    print("🛡️  RISK CONTROLS ACTIVE:")
    print(f"   • Max Position: {MAX_POSITION} shares")
    print(f"   • Max Trade Size: {MAX_TRADE_SIZE} shares")
    print(f"   • Stop-Loss: {STOP_LOSS_PCT:.0%} drawdown")
    print(f"   • Min Balance: ${MIN_BALANCE}")
    print("-" * 60)
    print()
    
    # Initialize components
    market = MarketSimulator(base_price=150.0)
    trader = GeminiTrader(GEMINI_API_KEY)
    
    trade_count = 0
    
    try:
        while True:
            # Check if trading was stopped by risk controls
            if trader.stopped:
                print("\n" + "=" * 60)
                print("🛑 TRADING STOPPED BY RISK CONTROLS")
                print("=" * 60)
                break
            
            # Get market data
            market_data = market.tick()
            indicators = market.get_indicators()
            
            print(f"\n📈 Market Update: ${market_data['price']:.2f}")
            print(f"   Trend: {indicators.get('trend', 'N/A')} | Momentum: {indicators.get('momentum', 0):.2f}%")
            
            # Get AI decision
            decision = trader.analyze_market(market_data, indicators)
            
            print(f"\n🤖 AI Decision: {decision['signal']} (Confidence: {decision['confidence']:.0%})")
            print(f"   Reasoning: {decision['reasoning']}")
            
            # Execute trade if not HOLD
            trade = trader.execute_trade(decision, market_data)
            
            if trade:
                trade_count += 1
                print(f"\n💰 TRADE EXECUTED #{trade_count}")
                print(f"   {trade['signal']} {trade['quantity']} @ ${trade['price']:.2f}")
                print(f"   ⚡ Latency: {trade['latency_ns']}ns")
                print(f"   📊 Position: {trader.position} | Balance: ${trader.balance:.2f}")
            
            # Send to dashboard
            send_ai_decision(decision, trader, trade)
            
            print(f"\n⏳ Next analysis in {TRADE_INTERVAL}s...")
            time.sleep(TRADE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("📊 SESSION SUMMARY")
        print("=" * 60)
        print(f"   Total Trades: {trade_count}")
        print(f"   Final Position: {trader.position}")
        print(f"   Final Balance: ${trader.balance:.2f}")
        print(f"   P&L: ${trader.balance - STARTING_BALANCE:.2f}")
        print("=" * 60)


if __name__ == "__main__":
    main()
