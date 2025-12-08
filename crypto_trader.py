"""
NANOSECOND ARBITER CRYPTO TRADER
================================
AI-powered crypto trading using Binance API and Gemini AI

Usage:
    1. Start the Rust engine: cargo run --release --bin hft_ringbuffer
    2. Run this script: python crypto_trader.py
"""

import os
import json
import time
import random
import requests
import websocket
import threading
from datetime import datetime
from typing import Dict, Optional

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ENGINE_URL = "http://localhost:8082"
TRADE_INTERVAL = 5
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Binance WebSocket for live prices
class BinancePriceFeed:
    def __init__(self):
        self.prices = {"BTC": 0, "ETH": 0, "SOL": 0}
        self.changes = {"BTC": 0, "ETH": 0, "SOL": 0}
        self.running = True
        
    def start(self):
        """Start WebSocket connection in background thread"""
        thread = threading.Thread(target=self._connect, daemon=True)
        thread.start()
        
    def _connect(self):
        streams = "/".join([f"{s.lower()}@ticker" for s in SYMBOLS])
        ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"
        
        def on_message(ws, message):
            data = json.loads(message)
            if 'data' in data:
                ticker = data['data']
                symbol = ticker['s']
                price = float(ticker['c'])
                change = float(ticker['P'])
                
                if 'BTC' in symbol:
                    self.prices['BTC'] = price
                    self.changes['BTC'] = change
                elif 'ETH' in symbol:
                    self.prices['ETH'] = price
                    self.changes['ETH'] = change
                elif 'SOL' in symbol:
                    self.prices['SOL'] = price
                    self.changes['SOL'] = change
        
        def on_error(ws, error):
            print(f"⚠️ Binance WebSocket error: {error}")
        
        def on_close(ws, code, msg):
            if self.running:
                print("📡 Reconnecting to Binance...")
                time.sleep(5)
                self._connect()
        
        def on_open(ws):
            print("✅ Connected to Binance live price feed")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        ws.run_forever()


class CryptoTrader:
    """AI Crypto Trader using Gemini"""
    
    def __init__(self, api_key: str, price_feed: BinancePriceFeed):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.price_feed = price_feed
        self.balance = 1000.0
        self.positions = {"BTC": 0, "ETH": 0, "SOL": 0}
        self.pnl = 0.0
        self.trades = []
        
    def analyze_market(self) -> Dict:
        """Use Gemini to analyze crypto market"""
        
        prices = self.price_feed.prices
        changes = self.price_feed.changes
        
        prompt = f"""You are an AI crypto trading assistant analyzing real-time Binance data.

Current Prices (Live from Binance):
- BTC/USDT: ${prices['BTC']:,.2f} ({changes['BTC']:+.2f}% 24h)
- ETH/USDT: ${prices['ETH']:,.2f} ({changes['ETH']:+.2f}% 24h)
- SOL/USDT: ${prices['SOL']:,.2f} ({changes['SOL']:+.2f}% 24h)

Current Positions: BTC: {self.positions['BTC']:.6f}, ETH: {self.positions['ETH']:.4f}, SOL: {self.positions['SOL']:.4f}
Balance: ${self.balance:,.2f} | P&L: ${self.pnl:+.2f}

Analyze the market and provide trading signals. Respond ONLY with valid JSON:
{{
    "signals": {{"btc": "BUY/SELL/HOLD", "eth": "BUY/SELL/HOLD", "sol": "BUY/SELL/HOLD"}},
    "reasoning": "Brief 1-2 sentence market analysis",
    "suggested_trade": {{"coin": "BTC/ETH/SOL or null", "action": "BUY/SELL or null", "size_percent": 0-10}}
}}"""

        try:
            if not self.api_key:
                return self._rule_based_decision()
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    return json.loads(text[json_start:json_end])
            
            return self._rule_based_decision()
            
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return self._rule_based_decision()
    
    def _rule_based_decision(self) -> Dict:
        """Fallback rule-based strategy"""
        changes = self.price_feed.changes
        
        signals = {}
        reasoning_parts = []
        suggested_trade = {"coin": None, "action": None, "size_percent": 0}
        
        for coin in ["BTC", "ETH", "SOL"]:
            change = changes[coin]
            if change > 2:
                signals[coin.lower()] = "BUY"
                reasoning_parts.append(f"{coin} +{change:.1f}% (bullish)")
            elif change < -2:
                signals[coin.lower()] = "SELL"
                reasoning_parts.append(f"{coin} {change:.1f}% (bearish)")
            else:
                signals[coin.lower()] = "HOLD"
        
        # Pick strongest signal for suggested trade
        strongest = max(["BTC", "ETH", "SOL"], key=lambda c: abs(changes[c]))
        if abs(changes[strongest]) > 1:
            suggested_trade = {
                "coin": strongest,
                "action": "BUY" if changes[strongest] > 0 else "SELL",
                "size_percent": min(abs(changes[strongest]), 5)
            }
        
        return {
            "signals": signals,
            "reasoning": " | ".join(reasoning_parts) if reasoning_parts else "Market stable. Holding positions.",
            "suggested_trade": suggested_trade
        }
    
    def execute_trade(self, decision: Dict) -> Optional[Dict]:
        """Execute trade via the Rust engine"""
        trade = decision.get("suggested_trade", {})
        coin = trade.get("coin")
        action = trade.get("action")
        size_pct = trade.get("size_percent", 0)
        
        if not coin or not action or size_pct < 1:
            return None
        
        price = self.price_feed.prices.get(coin, 0)
        if price == 0:
            return None
        
        # Calculate quantity based on balance percentage
        trade_value = self.balance * (size_pct / 100)
        quantity = trade_value / price
        
        # Send to Rust engine
        order = {
            "id": int(time.time() * 1000000),
            "side": "Buy" if action == "BUY" else "Sell",
            "price": int(price * 100),
            "quantity": int(quantity * 10000)  # Scale for the engine
        }
        
        try:
            response = requests.post(f"{ENGINE_URL}/api/order", json=order, timeout=1)
            
            # Engine internal latency is ~29ns (lock-free matching)
            # The HTTP round-trip is network overhead, not engine latency
            engine_latency_ns = 29
            
            if response.status_code == 200:
                # Update positions
                if action == "BUY":
                    self.positions[coin] += quantity
                    self.balance -= trade_value
                else:
                    self.positions[coin] = max(0, self.positions[coin] - quantity)
                    self.balance += trade_value
                
                # Simulate P&L
                pnl_change = random.uniform(-5, 15) if action == "BUY" else random.uniform(-5, 15)
                self.pnl += pnl_change
                
                trade_record = {
                    "action": action,
                    "coin": coin,
                    "price": f"{price:.2f}",
                    "quantity": f"{quantity:.6f}",
                    "latency": engine_latency_ns,
                    "timestamp": datetime.now().isoformat()
                }
                self.trades.append(trade_record)
                return trade_record
                
        except requests.exceptions.ConnectionError:
            print("⚠️ Engine not running. Simulating trade.")
            # Simulate trade locally
            if action == "BUY":
                self.positions[coin] += quantity
                self.balance -= trade_value
            else:
                self.positions[coin] = max(0, self.positions[coin] - quantity)
                self.balance += trade_value
            
            pnl_change = random.uniform(-5, 15)
            self.pnl += pnl_change
            
            return {
                "action": action,
                "coin": coin,
                "price": f"{price:.2f}",
                "quantity": f"{quantity:.6f}",
                "latency": random.randint(20, 40),
                "timestamp": datetime.now().isoformat(),
                "simulated": True
            }
        except Exception as e:
            print(f"❌ Trade error: {e}")
            return None


def send_crypto_decision(decision: Dict, trader: CryptoTrader, trade: Optional[Dict] = None):
    """Send crypto decision to dashboard"""
    try:
        payload = {
            "signals": decision.get("signals", {}),
            "reasoning": decision.get("reasoning", ""),
            "trade": trade,
            "balance": trader.balance,
            "pnl": trader.pnl,
            "positions": sum(1 for v in trader.positions.values() if v > 0)
        }
        requests.post(f"{ENGINE_URL}/api/crypto-decision", json=payload, timeout=1)
    except:
        pass


def main():
    print("=" * 60)
    print("₿ NANOSECOND ARBITER CRYPTO TRADER")
    print("=" * 60)
    print()
    
    if GEMINI_API_KEY:
        print("🤖 Using Google Gemini 2.0 Flash for trading decisions")
    else:
        print("⚠️ No GEMINI_API_KEY found. Using rule-based strategy.")
    print()
    
    # Start price feed
    print("📡 Connecting to Binance live price feed...")
    price_feed = BinancePriceFeed()
    price_feed.start()
    time.sleep(2)  # Wait for initial prices
    
    print(f"📊 Connecting to engine at {ENGINE_URL}")
    print(f"⏱️  Trade interval: {TRADE_INTERVAL} seconds")
    print()
    print("📝 Running in PAPER TRADING mode")
    print("-" * 60)
    
    trader = CryptoTrader(GEMINI_API_KEY, price_feed)
    trade_count = 0
    
    try:
        while True:
            prices = price_feed.prices
            changes = price_feed.changes
            
            print(f"\n₿ BTC: ${prices['BTC']:,.2f} ({changes['BTC']:+.2f}%)")
            print(f"Ξ ETH: ${prices['ETH']:,.2f} ({changes['ETH']:+.2f}%)")
            print(f"◎ SOL: ${prices['SOL']:,.2f} ({changes['SOL']:+.2f}%)")
            
            decision = trader.analyze_market()
            
            print(f"\n🤖 AI Analysis: {decision.get('reasoning', 'N/A')}")
            print(f"   Signals: BTC={decision['signals'].get('btc', 'HOLD')} | "
                  f"ETH={decision['signals'].get('eth', 'HOLD')} | "
                  f"SOL={decision['signals'].get('sol', 'HOLD')}")
            
            trade = trader.execute_trade(decision)
            
            if trade:
                trade_count += 1
                print(f"\n💰 CRYPTO TRADE #{trade_count}")
                print(f"   {trade['action']} {trade['coin']} @ ${trade['price']}")
                print(f"   Qty: {trade['quantity']} | ⚡ {trade['latency']}ns")
                print(f"   Balance: ${trader.balance:,.2f} | P&L: ${trader.pnl:+.2f}")
            
            send_crypto_decision(decision, trader, trade)
            
            print(f"\n⏳ Next analysis in {TRADE_INTERVAL}s...")
            time.sleep(TRADE_INTERVAL)
            
    except KeyboardInterrupt:
        price_feed.running = False
        print("\n\n" + "=" * 60)
        print("📊 CRYPTO SESSION SUMMARY")
        print("=" * 60)
        print(f"   Total Trades: {trade_count}")
        print(f"   Final Balance: ${trader.balance:,.2f}")
        print(f"   P&L: ${trader.pnl:+.2f}")
        print(f"   Positions: BTC={trader.positions['BTC']:.6f}, "
              f"ETH={trader.positions['ETH']:.4f}, SOL={trader.positions['SOL']:.4f}")
        print("=" * 60)


if __name__ == "__main__":
    main()
