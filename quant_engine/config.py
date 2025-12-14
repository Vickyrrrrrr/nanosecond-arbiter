# ============================================================================
# TRADING SYSTEM CONFIGURATION
# ============================================================================

# ASSETS
# ASSETS
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
# MULTI-TIMEFRAME CONFIG
TIMEFRAMES = ["15m", "5m"] # Higher to Lower
TIMEFRAME_WEIGHTS = {
    "15m": 0.6,
    "5m": 0.4
}
CONFIDENCE_THRESHOLD = 0.7  # Mini score required to trade


# HYBRID RISK LIMITS
RISK_SPOT = 0.01            # 1% for Spot
RISK_FUTURES = 0.005        # 0.5% for Futures

MAX_DAILY_LOSS = 0.02       # 2% of Combined Equity
MAX_TRADES_PER_DAY = 6
COOLDOWN_CANDLES = 5

# LEVERAGE LIMITS (Futures Only)
LEVERAGE_MAP = {
    "BTCUSDT": 3,
    "ETHUSDT": 3,
    "SOLUSDT": 2
}

# STRATEGY PARAMETERS
RSI_LONG_MIN = 40
RSI_LONG_MAX = 50
RSI_SHORT_MIN = 55
RSI_SHORT_MAX = 65

EMA_FAST = 50
EMA_SLOW = 200

# SAFETY
SLIPPAGE_TOLERANCE = 0.002
