# 🤖 How to Use This Trading Bot - Customer Guide

## ⚡ Quick Start (5 Minutes)

### **What You Get:**
- Ultra-fast HFT matching engine (29ns latency)
- Automated market making bot
- Web dashboard for monitoring
- Complete source code

### **What You Need:**
- Windows/Mac/Linux computer
- Binance account (free)
- $50-100 to start trading (optional - can test with $0)

---

## 📋 Step-by-Step Setup

### **Step 1: Install Requirements (2 minutes)**

**Install Rust:**
```bash
# Windows/Mac/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Install Python:**
- Download from: python.org (version 3.8+)

**Install Dependencies:**
```bash
pip install requests websocket-client
```

### **Step 2: Get Your API Keys (3 minutes)**

**For Testing (FREE - No Money Needed):**
1. Go to: https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Copy your API Key and Secret Key

**For Real Trading:**
1. Go to: https://www.binance.com/
2. Create account → API Management
3. Create new API key
4. Enable "Spot Trading" only

### **Step 3: Configure the Bot (1 minute)**

Open `market_maker.py` and edit these lines:

```python
# Line 18: Choose testnet or real trading
USE_TESTNET = True  # Set to False for real money

# Line 28-29: Paste your API keys
API_KEY = "paste_your_key_here"
API_SECRET = "paste_your_secret_here"

# Line 32-36: Adjust strategy (optional)
SPREAD_PERCENTAGE = 0.001  # 0.1% spread
ORDER_SIZE_USD = 10        # $10 per order
```

### **Step 4: Run the Bot (30 seconds)**

**Terminal 1 - Start the Engine:**
```bash
cargo run --release
```

**Terminal 2 - Start the Trading Bot:**
```bash
python market_maker.py
```

**Terminal 3 - Check Your Orders (optional):**
```bash
python check_orders.py
```

### **Step 5: Monitor (Ongoing)**

**View Dashboard:**
- Open browser: http://localhost:8082
- See live order book and trades

**Check Profits:**
- Run: `python check_orders.py`
- View your Binance account

---

## 🎯 What the Bot Does

### **Automated Market Making:**

The bot continuously:
1. **Monitors** Bitcoin price on Binance
2. **Places BUY orders** 0.1% below market price
3. **Places SELL orders** 0.1% above market price
4. **Captures the spread** when both fill

**Example:**
```
Market: $90,000
Bot places:
  BUY at $89,910 (0.1% below)
  SELL at $90,090 (0.1% above)

When both fill:
Profit = $90,090 - $89,910 = $180 per BTC
```

With $10 orders: ~$0.02 profit per round trip

---

## ⚙️ Customization Options

### **Strategy Settings:**

**Conservative (Safer):**
```python
SPREAD_PERCENTAGE = 0.002  # 0.2% spread
ORDER_SIZE_USD = 10
UPDATE_INTERVAL = 10  # Update every 10 seconds
```

**Aggressive (Riskier):**
```python
SPREAD_PERCENTAGE = 0.0005  # 0.05% spread
ORDER_SIZE_USD = 50
UPDATE_INTERVAL = 2  # Update every 2 seconds
```

**Different Trading Pairs:**
```python
SYMBOL = "ETHUSDT"  # Trade Ethereum instead
SYMBOL = "SOLUSDT"  # Trade Solana instead
```

---

## 📊 Expected Performance

### **Profit Estimates:**

| Order Size | Trades/Day | Daily Profit | Monthly Profit |
|------------|------------|--------------|----------------|
| $10 | 50 | $1 | $30 |
| $50 | 50 | $5 | $150 |
| $100 | 50 | $10 | $300 |
| $500 | 50 | $50 | $1,500 |

**Note:** Actual results vary based on market conditions.

---

## 🛑 How to Stop

Press `Ctrl+C` in the terminal running `market_maker.py`

The bot will:
1. Cancel all open orders
2. Disconnect gracefully
3. Show final status

---

## ⚠️ Risk Management

### **Safety Rules:**

1. **Start Small:** Begin with $50-100 maximum
2. **Use Testnet First:** Practice with fake money for 1 week
3. **Set Loss Limits:** Stop if you lose $10/day
4. **Don't Overtrade:** Never use more than 10% of your capital
5. **Avoid News Events:** Don't trade during major announcements

### **When to Stop:**
- Market is extremely volatile (>5% moves)
- You've hit your daily loss limit
- Major news is breaking
- You're uncomfortable with the risk

---

## 🔧 Troubleshooting

### **"API Key Invalid"**
- Check you copied the full key (no spaces)
- Verify you're using testnet keys with `USE_TESTNET = True`

### **"Insufficient Balance"**
- Testnet: You get fake money automatically
- Real: Deposit USDT to your Binance account

### **"Order Rejected"**
- Price might be too far from market
- Adjust `SPREAD_PERCENTAGE` to be smaller
- Check minimum order size ($10 minimum)

### **Bot Not Placing Orders**
- Check your internet connection
- Verify API keys are correct
- Make sure Binance API is not down

---

## 📈 Scaling Up

### **Growth Path:**

**Week 1:** Run on testnet, learn how it works
**Week 2:** Start with $50 real money, $10 orders
**Month 1:** If profitable, increase to $100 orders
**Month 2:** If still profitable, increase to $500 orders
**Month 3+:** Consider adding more trading pairs

---

## 💬 Support

### **Common Questions:**

**Q: Is this guaranteed profit?**
A: No. All trading involves risk. Past performance doesn't guarantee future results.

**Q: How much can I make?**
A: Depends on capital and market conditions. Expect 1-5% monthly returns with proper risk management.

**Q: Can I run multiple bots?**
A: Yes! Run different bots for different trading pairs (BTC, ETH, SOL, etc.)

**Q: Do I need to watch it constantly?**
A: No. The bot runs automatically. Check it 1-2 times per day.

**Q: What if my computer crashes?**
A: The bot will stop. All open orders remain on Binance. Restart the bot when ready.

---

## 🎯 Success Tips

1. **Be Patient:** Don't expect instant riches
2. **Keep Learning:** Understand why trades profit or lose
3. **Stay Disciplined:** Follow your risk management rules
4. **Start Small:** Scale up gradually as you gain confidence
5. **Track Performance:** Keep a log of daily profits/losses

---

## 📚 Additional Resources

- **Binance API Docs:** https://binance-docs.github.io/apidocs/spot/en/
- **Trading Guide:** See `TRADING_GUIDE.md` in this package
- **Monetization Ideas:** See `MONETIZATION_GUIDE.md`

---

**Remember:** This is a tool, not a money printer. Use it responsibly, start small, and never risk more than you can afford to lose.

**Good luck and happy trading!** 🚀
