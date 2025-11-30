# 🤖 Market Making Bot - Setup Guide

## What This Does
This bot automatically trades on Binance by:
1. Monitoring Bitcoin (BTC) price in real-time
2. Placing buy orders slightly below market price
3. Placing sell orders slightly above market price
4. Profiting from the spread when both fill

## ⚠️ CRITICAL WARNINGS
- **This uses REAL money** - You can lose everything
- **Start with TESTNET** (fake money) to learn first
- **Never invest more than you can afford to lose**
- **Markets are unpredictable** - No strategy is guaranteed

## 🧪 Step 1: Get Testnet API Keys (FREE - No Risk)

1. Go to: https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Save your:
   - API Key (looks like: `abc123...`)
   - Secret Key (looks like: `xyz789...`)

## 💰 Step 2: Get Real API Keys (ONLY after testing!)

1. Go to: https://www.binance.com/
2. Create account and verify identity
3. Go to API Management
4. Create new API key
5. **IMPORTANT:** Enable "Spot Trading" only (NOT Futures!)

## 🔧 Step 3: Configure the Bot

Edit `market_maker.py`:

```python
# Line 18: Set to True for testing, False for real trading
USE_TESTNET = True  # Keep this True until you're confident!

# Line 28-29: Paste your API keys
API_KEY = "paste_your_api_key_here"
API_SECRET = "paste_your_secret_key_here"

# Line 32-36: Adjust strategy (optional)
SPREAD_PERCENTAGE = 0.001  # 0.1% spread (lower = more trades, less profit per trade)
ORDER_SIZE_USD = 10  # Size of each order ($10 is safe for testing)
```

## 🚀 Step 4: Run the Bot

### Make sure your Rust engine is running:
```bash
cargo run --bin hft_ringbuffer
```

### In a new terminal, run the market maker:
```bash
python market_maker.py
```

## 📊 What You'll See

```
🤖 MARKET MAKING BOT STARTING
============================================================
🧪 TESTNET MODE - Using fake money
✅ Connected to Local Engine at 127.0.0.1:8083
💰 Checking account balance...
   Balances: {'BTC': 1.0, 'USDT': 10000.0}

📊 Trading Configuration:
   Symbol: BTCUSDT
   Spread: 0.1%
   Order Size: $10
   Update Interval: 5s

🚀 Starting market making loop...
   Press Ctrl+C to stop

📈 Market: $90611.00 | Bid: $90520.39 | Ask: $90701.61
   📥 Placing BUY order: 0.000110 @ $90520.39
   📤 Placing SELL order: 0.000110 @ $90701.61
```

## 💡 How It Makes Money

**Example Trade:**
1. Bot places BUY at $90,520 (0.1% below market)
2. Bot places SELL at $90,702 (0.1% above market)
3. If both fill, you profit: $90,702 - $90,520 = **$182 per BTC**
4. With $10 orders, profit = $0.02 per round trip
5. If you do 100 trades/day = **$2/day** = **$60/month**

**Scaling:**
- $100 orders = $600/month
- $1000 orders = $6000/month

## 🎯 Strategy Tuning

### Conservative (Safer, Slower)
```python
SPREAD_PERCENTAGE = 0.002  # 0.2% spread
ORDER_SIZE_USD = 10
UPDATE_INTERVAL = 10  # Update every 10 seconds
```

### Aggressive (Riskier, Faster)
```python
SPREAD_PERCENTAGE = 0.0005  # 0.05% spread
ORDER_SIZE_USD = 50
UPDATE_INTERVAL = 2  # Update every 2 seconds
```

## 🛑 How to Stop

Press `Ctrl+C` in the terminal. The bot will:
1. Cancel all open orders
2. Disconnect gracefully
3. Show final status

## 📈 Monitoring Performance

### Check your dashboard:
Open http://localhost:8082 to see:
- Live order book
- Your orders being placed
- Execution speed

### Check Binance:
- Testnet: https://testnet.binance.vision/
- Real: https://www.binance.com/en/my/orders/exchange/tradeorder

## ⚠️ Common Issues

### "API Key Invalid"
- Double-check you copied the full key (no spaces)
- Make sure you're using testnet keys with `USE_TESTNET = True`

### "Insufficient Balance"
- Testnet gives you fake money automatically
- Real account needs you to deposit USDT

### "Order Rejected"
- Price might be too far from market (adjust `SPREAD_PERCENTAGE`)
- Quantity might be too small (Binance minimum is ~$10)

## 🎓 Learning Path

1. **Week 1:** Run on testnet, watch it work
2. **Week 2:** Try different spread percentages
3. **Week 3:** Start with $50 real money (if confident)
4. **Month 2:** Scale to $500 if profitable
5. **Month 3+:** Consider advanced strategies

## 🚨 Risk Management Rules

1. **Never use more than 5% of your total capital** per trade
2. **Set a daily loss limit** (e.g., stop if you lose $50/day)
3. **Don't trade during high volatility** (news events, crashes)
4. **Keep 50% in stablecoins** (USDT) as a buffer

## 📚 Next Steps

Once this works, you can:
1. Add more trading pairs (ETH, SOL, etc.)
2. Implement stop-loss orders
3. Add profit tracking and reporting
4. Build a web dashboard for monitoring
5. Scale to multiple exchanges

## 💬 Support

If you get stuck:
1. Check the error message carefully
2. Google the error (Binance API errors are well-documented)
3. Start with smaller order sizes
4. Test on testnet first!

---

**Remember:** This is a learning tool. Real trading requires experience, capital, and risk management. Start small, learn continuously, and never risk money you can't afford to lose.
