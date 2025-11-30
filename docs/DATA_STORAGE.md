# 📊 Where Order Data Is Stored

## Overview

Your HFT system stores order data in **3 different locations**, each serving a different purpose:

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA STORAGE LOCATIONS                   │
└─────────────────────────────────────────────────────────────┘

1️⃣ BINANCE TESTNET (Cloud)
   └─ Real executed trades
   └─ Account balances
   └─ Order history
   
2️⃣ RUST MATCHING ENGINE (RAM - Temporary)
   └─ Active order book
   └─ Pending buy/sell orders
   └─ Real-time order matching
   
3️⃣ LOCAL JSON FILES (Disk - Permanent)
   └─ Daily performance reports
   └─ Trade history snapshots
   └─ Balance tracking
```

---

## 1️⃣ Binance Testnet (Cloud Storage)

**Location:** Binance's servers (cloud)

**What's Stored:**
- All executed trades (when orders fill)
- Account balances (BTC, USDT, etc.)
- Open orders waiting to be filled
- Order history (last 100 trades)

**How to Access:**
```bash
python check_orders.py      # See current open orders
python track_performance.py # Get trade history
```

**Example Data:**
```json
{
  "balances": {
    "BTC": 1.00011,
    "USDT": 9990.21
  },
  "open_orders": [
    {
      "side": "BUY",
      "price": 91202.23,
      "quantity": 0.01094
    }
  ]
}
```

**Persistence:** ✅ **Permanent** - Data stays even if you turn off your bot

---

## 2️⃣ Rust Matching Engine (RAM - In-Memory)

**Location:** Your computer's RAM (temporary memory)

**What's Stored:**
```rust
pub struct OrderBook {
    bids: BTreeMap<u64, Vec<Order>>,  // Buy orders sorted by price
    asks: BTreeMap<u64, Vec<Order>>,  // Sell orders sorted by price
}
```

**Data Structure:**
```
ORDER BOOK (In RAM):

BIDS (Buy Orders):                ASKS (Sell Orders):
Price: $91,202  → [Order1]        Price: $91,568  → [Order1]
Price: $91,150  → [Order2]        Price: $91,620  → [Order2]
Price: $91,100  → [Order3]        Price: $91,670  → [Order3]
```

**How It Works:**
1. Python bot sends order → TCP Gateway (port 8083)
2. Gateway pushes to Ring Buffer (lock-free queue)
3. Matching Engine pops from buffer → Adds to OrderBook
4. OrderBook stored in RAM using `BTreeMap` (sorted tree)

**Access Method:**
- HTTP API: `http://localhost:8082/api/orderbook`
- Returns JSON of current order book state

**Persistence:** ❌ **Temporary** - Lost when you stop the Rust engine

**Why RAM?**
- **Speed:** 29 nanoseconds per order
- **Lock-free:** No mutex overhead
- **Real-time:** Instant order matching

---

## 3️⃣ Local JSON Files (Disk Storage)

**Location:** `C:\HFT-2\performance_YYYYMMDD.json`

**What's Stored:**
- Daily snapshots of account balances
- Trade history (buys/sells)
- Profit/Loss calculations
- Performance metrics

**Example File:** `performance_20251130.json`

```json
{
  "date": "2025-11-30",
  "time": "12:45:29",
  "balances": {
    "BTC": {
      "free": 1.0,
      "locked": 0.00011
    },
    "USDT": {
      "free": 9980.02,
      "locked": 9.99
    }
  },
  "trades": {
    "total_buys": 5,
    "total_sells": 3,
    "pnl": 12.50,
    "avg_buy_price": 91200.00,
    "avg_sell_price": 91450.00
  },
  "total_trades": 8
}
```

**How to Generate:**
```bash
python track_performance.py
```

**Persistence:** ✅ **Permanent** - Saved to disk, survives restarts

---

## 📊 Data Flow Diagram

```
┌─────────────────────┐
│  PYTHON BOT         │
│  (market_maker.py)  │
└──────────┬──────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ↓                                 ↓
┌─────────────────────┐          ┌─────────────────────┐
│  BINANCE TESTNET    │          │  RUST ENGINE        │
│  (Cloud)            │          │  (RAM)              │
├─────────────────────┤          ├─────────────────────┤
│ ✅ Executed Trades  │          │ ⚡ Active OrderBook │
│ ✅ Account Balance  │          │ ⚡ Pending Orders   │
│ ✅ Open Orders      │          │ ⚡ Real-time Match  │
│                     │          │                     │
│ PERMANENT STORAGE   │          │ TEMPORARY (RAM)     │
└─────────────────────┘          └─────────────────────┘
           │                                 │
           │                                 │
           ↓                                 ↓
┌──────────────────────────────────────────────────────┐
│  PERFORMANCE TRACKER                                 │
│  (track_performance.py)                              │
└──────────┬───────────────────────────────────────────┘
           │
           ↓
┌─────────────────────┐
│  LOCAL JSON FILES   │
│  (Disk)             │
├─────────────────────┤
│ 📁 performance_*.json
│                     │
│ ✅ Daily Reports    │
│ ✅ Trade History    │
│ ✅ PnL Tracking     │
│                     │
│ PERMANENT STORAGE   │
└─────────────────────┘
```

---

## 🔍 How to View Each Storage

### View Binance Data (Cloud)

**Check Current Orders:**
```bash
python check_orders.py
```

**Output:**
```
📋 Open Orders (BTCUSDT):
   📥 BUY: 0.01094 BTC @ $91,202.23
   📤 SELL: 0.01094 BTC @ $91,567.77

Total Open Orders: 2
```

**Get Trade History:**
```bash
python track_performance.py
```

---

### View Rust Engine Data (RAM)

**Method 1: HTTP API**
```bash
curl http://localhost:8082/api/orderbook
```

**Method 2: Web Browser**
```
http://localhost:8082/api/orderbook
```

**Returns:**
```json
{
  "bids": [
    {
      "price": 91202,
      "orders": [
        {"id": 123, "quantity": 0.01094}
      ]
    }
  ],
  "asks": [
    {
      "price": 91568,
      "orders": [
        {"id": 124, "quantity": 0.01094}
      ]
    }
  ]
}
```

---

### View Local Files (Disk)

**List Performance Files:**
```bash
dir performance_*.json
```

**View Today's Report:**
```bash
python track_performance.py
```

**Manually Open File:**
```
C:\HFT-2\performance_20251130.json
```

---

## 💾 Storage Comparison

| Feature | Binance (Cloud) | Rust Engine (RAM) | JSON Files (Disk) |
|---------|----------------|-------------------|-------------------|
| **Speed** | Slow (API calls) | Ultra-fast (29ns) | Medium (disk I/O) |
| **Persistence** | ✅ Permanent | ❌ Temporary | ✅ Permanent |
| **Capacity** | Unlimited | Limited by RAM | Limited by disk |
| **Access** | Python scripts | HTTP API | File system |
| **Purpose** | Real trading | Order matching | Performance tracking |
| **Survives Restart** | ✅ Yes | ❌ No | ✅ Yes |

---

## 🎯 What Happens to Data When You Stop the Bot?

### If You Stop Python Bot:
- ✅ Binance data: **SAFE** (stays in cloud)
- ❌ Rust engine: **KEEPS RUNNING** (if not stopped)
- ✅ JSON files: **SAFE** (on disk)

### If You Stop Rust Engine:
- ✅ Binance data: **SAFE** (stays in cloud)
- ❌ Order book in RAM: **LOST** (cleared from memory)
- ✅ JSON files: **SAFE** (on disk)

### If You Restart Computer:
- ✅ Binance data: **SAFE** (stays in cloud)
- ❌ Rust engine: **STOPPED** (need to restart)
- ❌ Python bot: **STOPPED** (need to restart)
- ✅ JSON files: **SAFE** (on disk)

---

## 📝 Important Notes

### Rust Engine RAM Storage

**Why temporary?**
- Designed for **speed**, not persistence
- Lock-free data structures don't serialize well
- Real HFT systems use RAM for hot data

**What if you need persistence?**
You could add database storage (PostgreSQL, Redis) but it would:
- ❌ Increase latency (29ns → 1000ns+)
- ❌ Add complexity
- ❌ Reduce throughput

### JSON File Storage

**Current file:** `performance_20251130.json` (30KB)

**Contains:**
- 1,822 lines of data
- All balances (100+ cryptocurrencies)
- Complete trade history
- PnL calculations

**New file created daily** when you run `track_performance.py`

---

## 🚀 Recommended Workflow

### Daily Routine:

**Morning:**
```bash
# Check if bots are running
# (Look for terminal windows)
```

**Evening:**
```bash
# Generate daily report
python track_performance.py

# This creates/updates: performance_YYYYMMDD.json
```

**Weekly:**
```bash
# Run tracker to see weekly analysis
python track_performance.py

# Shows:
# - Daily breakdown
# - Total PnL
# - Win rate
# - Recommendations
```

---

## 🔐 Data Security

### Binance (Cloud):
- Protected by API keys
- Testnet = fake money (safe to experiment)
- Real money = enable 2FA, IP whitelist

### Rust Engine (RAM):
- Only accessible on localhost (127.0.0.1)
- No external access
- Cleared on restart (no data leakage)

### JSON Files (Disk):
- Stored locally on your computer
- Contains testnet data (not sensitive)
- Can be backed up to cloud if needed

---

## 💡 Summary

**3 Storage Locations:**

1. **Binance** = Real source of truth (executed trades, balances)
2. **Rust Engine** = Ultra-fast temporary cache (active orders)
3. **JSON Files** = Historical records (performance tracking)

**Data Flow:**
```
Orders → Binance (permanent) + Rust (temporary)
Daily → Python tracker → JSON files (permanent)
```

**To view everything:**
```bash
python check_orders.py      # Binance current orders
curl localhost:8082/api/orderbook  # Rust order book
python track_performance.py # Historical data
```

That's it! Your data is safe and accessible from multiple locations. 🎉
