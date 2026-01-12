"""
Trend Momentum Volatility Strategy
===================================
A comprehensive crypto trading strategy that combines:
- EMA Trend Analysis (50/100/200)
- RSI Momentum Filter
- ATR-based Stop Loss and Take Profit
- Volume Confirmation

Supports:
- Spot (Long only)
- Futures (Long + Short)
- Multi-timeframe: 5m, 15m, 1h
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================
# STRATEGY CONFIGURATION
# ============================================================
STRATEGY_NAME = "TREND_MOMENTUM_VOLATILITY"

# Timeframes
TIMEFRAMES = ["5m", "15m", "1h"]

# EMA Parameters
EMA_FAST = 50
EMA_MID = 100
EMA_SLOW = 200

# Indicator Periods
RSI_PERIOD = 14
ATR_PERIOD = 14
VOLUME_PERIOD = 20

# Risk Management
RISK_PER_TRADE = 0.01  # 1% risk per trade
SL_ATR_MULTIPLIER = 1.5
TP_ATR_MULTIPLIER = 3.0
BREAKEVEN_ATR = 1.0
TRAIL_ATR = 1.0


class MarketType(Enum):
    SPOT = "SPOT"
    FUTURES = "FUTURES"


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalType(Enum):
    LONG_ENTRY = "LONG_ENTRY"
    SHORT_ENTRY = "SHORT_ENTRY"
    NO_SIGNAL = "NO_SIGNAL"


@dataclass
class TradeSignal:
    """Represents a validated trade signal."""
    symbol: str
    timeframe: str
    signal_type: SignalType
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    atr: float
    rsi: float
    volume_ratio: float
    timestamp: int


@dataclass
class PositionState:
    """Track active position for trailing stop logic."""
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    atr_at_entry: float
    breakeven_hit: bool = False


class TrendMomentumVolatilityStrategy:
    """
    Trend Momentum Volatility Trading Strategy.
    
    Uses:
    - EMA 50/100/200 for trend direction
    - RSI 14 for momentum confirmation
    - ATR 14 for volatility-based SL/TP
    - Volume confirmation
    """
    
    def __init__(self, symbol: str, market_type: MarketType = MarketType.FUTURES):
        self.symbol = symbol
        self.market_type = market_type
        self.active_position: Optional[PositionState] = None
        
    # =========================================================================
    # INDICATOR CALCULATIONS
    # =========================================================================
    
    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def find_previous_resistance(df: pd.DataFrame, lookback: int = 20) -> float:
        """Find previous resistance (swing high)."""
        if len(df) < lookback:
            return df['high'].max()
        return df['high'].iloc[-(lookback+1):-1].max()
    
    @staticmethod
    def find_previous_support(df: pd.DataFrame, lookback: int = 20) -> float:
        """Find previous support (swing low)."""
        if len(df) < lookback:
            return df['low'].min()
        return df['low'].iloc[-(lookback+1):-1].min()
    
    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        Analyze market trend using EMAs.
        
        TREND_BULL = CLOSE > EMA_200 AND EMA_50 > EMA_100 AND EMA_100 > EMA_200
        TREND_BEAR = CLOSE < EMA_200 AND EMA_50 < EMA_100 AND EMA_100 < EMA_200
        """
        if len(df) < EMA_SLOW:
            return {"trend": Direction.NEUTRAL, "ema_50": 0, "ema_100": 0, "ema_200": 0}
        
        close = df['close']
        
        ema_50 = self.calculate_ema(close, EMA_FAST).iloc[-1]
        ema_100 = self.calculate_ema(close, EMA_MID).iloc[-1]
        ema_200 = self.calculate_ema(close, EMA_SLOW).iloc[-1]
        current_close = close.iloc[-1]
        
        # Bullish Trend Conditions
        trend_bull = (
            current_close > ema_200 and
            ema_50 > ema_100 and
            ema_100 > ema_200
        )
        
        # Bearish Trend Conditions
        trend_bear = (
            current_close < ema_200 and
            ema_50 < ema_100 and
            ema_100 < ema_200
        )
        
        if trend_bull:
            trend = Direction.LONG
        elif trend_bear:
            trend = Direction.SHORT
        else:
            trend = Direction.NEUTRAL
            
        return {
            "trend": trend,
            "ema_50": ema_50,
            "ema_100": ema_100,
            "ema_200": ema_200,
            "close": current_close
        }
    
    # =========================================================================
    # SIGNAL GENERATION
    # =========================================================================
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        account_balance: float = 10000.0,
        timestamp: int = 0
    ) -> Optional[TradeSignal]:
        """
        Generate trading signal based on Trend Momentum Volatility rules.
        
        Args:
            df: OHLCV DataFrame with at least 200 candles
            account_balance: Current account balance for position sizing
            timestamp: Current timestamp
            
        Returns:
            TradeSignal if valid entry, None otherwise
        """
        # Need enough data for EMA 200
        if len(df) < EMA_SLOW + 10:
            print(f"   ⚪ {self.symbol}: Not enough data ({len(df)} candles, need {EMA_SLOW + 10})")
            return None
        
        close = df['close']
        volume = df['volume']
        current_close = close.iloc[-1]
        
        # Calculate all indicators
        rsi = self.calculate_rsi(close, RSI_PERIOD).iloc[-1]
        atr = self.calculate_atr(df, ATR_PERIOD).iloc[-1]
        avg_volume = self.calculate_sma(volume, VOLUME_PERIOD).iloc[-1]
        current_volume = volume.iloc[-1]
        
        # Get trend analysis
        trend_data = self.analyze_trend(df)
        trend = trend_data["trend"]
        
        # Get support/resistance levels
        prev_resistance = self.find_previous_resistance(df)
        prev_support = self.find_previous_support(df)
        
        # =====================================================================
        # NO TRADE FILTER
        # Skip if RSI is extreme or volume is low
        # =====================================================================
        if rsi > 70 or rsi < 30:
            print(f"   🚫 {self.symbol}: RSI extreme ({rsi:.1f}) - No trade")
            return None
            
        if current_volume < avg_volume:
            print(f"   🚫 {self.symbol}: Volume below average ({current_volume:.0f} < {avg_volume:.0f}) - No trade")
            return None
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # =====================================================================
        # LONG ENTRY CHECK
        # =====================================================================
        if trend == Direction.LONG:
            # RSI in bullish zone (45-65)
            rsi_ok = 45 <= rsi <= 65
            # Close above previous resistance (breakout)
            breakout = current_close > prev_resistance
            # Volume confirmation
            volume_ok = current_volume > avg_volume
            
            if rsi_ok and breakout and volume_ok:
                entry_price = current_close
                stop_loss = entry_price - (atr * SL_ATR_MULTIPLIER)
                take_profit = entry_price + (atr * TP_ATR_MULTIPLIER)
                
                # Position sizing based on risk
                risk_amount = account_balance * RISK_PER_TRADE
                risk_distance = entry_price - stop_loss
                position_size = risk_amount / risk_distance if risk_distance > 0 else 0
                
                print(f"   ✅ {self.symbol} LONG Signal: RSI={rsi:.1f}, ATR={atr:.2f}, Vol={volume_ratio:.1f}x")
                
                return TradeSignal(
                    symbol=self.symbol,
                    timeframe="5m",
                    signal_type=SignalType.LONG_ENTRY,
                    direction=Direction.LONG,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=position_size,
                    atr=atr,
                    rsi=rsi,
                    volume_ratio=volume_ratio,
                    timestamp=timestamp
                )
            else:
                reasons = []
                if not rsi_ok: reasons.append(f"RSI={rsi:.1f} not in 45-65")
                if not breakout: reasons.append(f"No breakout (close={current_close:.2f} < res={prev_resistance:.2f})")
                if not volume_ok: reasons.append("Volume low")
                print(f"   ⚪ {self.symbol} LONG: {', '.join(reasons)}")
        
        # =====================================================================
        # SHORT ENTRY CHECK (Futures only)
        # =====================================================================
        if self.market_type == MarketType.FUTURES and trend == Direction.SHORT:
            # RSI in bearish zone (35-55)
            rsi_ok = 35 <= rsi <= 55
            # Close below previous support (breakdown)
            breakdown = current_close < prev_support
            # Volume confirmation
            volume_ok = current_volume > avg_volume
            
            if rsi_ok and breakdown and volume_ok:
                entry_price = current_close
                stop_loss = entry_price + (atr * SL_ATR_MULTIPLIER)
                take_profit = entry_price - (atr * TP_ATR_MULTIPLIER)
                
                # Position sizing based on risk
                risk_amount = account_balance * RISK_PER_TRADE
                risk_distance = stop_loss - entry_price
                position_size = risk_amount / risk_distance if risk_distance > 0 else 0
                
                print(f"   ✅ {self.symbol} SHORT Signal: RSI={rsi:.1f}, ATR={atr:.2f}, Vol={volume_ratio:.1f}x")
                
                return TradeSignal(
                    symbol=self.symbol,
                    timeframe="5m",
                    signal_type=SignalType.SHORT_ENTRY,
                    direction=Direction.SHORT,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=position_size,
                    atr=atr,
                    rsi=rsi,
                    volume_ratio=volume_ratio,
                    timestamp=timestamp
                )
            else:
                reasons = []
                if not rsi_ok: reasons.append(f"RSI={rsi:.1f} not in 35-55")
                if not breakdown: reasons.append(f"No breakdown (close={current_close:.2f} > sup={prev_support:.2f})")
                if not volume_ok: reasons.append("Volume low")
                print(f"   ⚪ {self.symbol} SHORT: {', '.join(reasons)}")
        
        return None
    
    # =========================================================================
    # POSITION MANAGEMENT (Trailing Stop & Breakeven)
    # =========================================================================
    
    def update_position(self, current_price: float, current_atr: float) -> Optional[float]:
        """
        Update position with trailing stop logic.
        
        Returns new stop loss if updated, None otherwise.
        """
        if self.active_position is None:
            return None
            
        pos = self.active_position
        new_stop = pos.stop_loss
        
        if pos.direction == Direction.LONG:
            # Check breakeven
            breakeven_level = pos.entry_price + (pos.atr_at_entry * BREAKEVEN_ATR)
            if not pos.breakeven_hit and current_price >= breakeven_level:
                new_stop = pos.entry_price
                pos.breakeven_hit = True
                print(f"   🔒 {self.symbol} LONG: Breakeven activated at {pos.entry_price:.2f}")
            
            # Trailing stop
            trail_stop = current_price - (current_atr * TRAIL_ATR)
            new_stop = max(new_stop, trail_stop)
            
        elif pos.direction == Direction.SHORT:
            # Check breakeven
            breakeven_level = pos.entry_price - (pos.atr_at_entry * BREAKEVEN_ATR)
            if not pos.breakeven_hit and current_price <= breakeven_level:
                new_stop = pos.entry_price
                pos.breakeven_hit = True
                print(f"   🔒 {self.symbol} SHORT: Breakeven activated at {pos.entry_price:.2f}")
            
            # Trailing stop
            trail_stop = current_price + (current_atr * TRAIL_ATR)
            new_stop = min(new_stop, trail_stop)
        
        if new_stop != pos.stop_loss:
            pos.stop_loss = new_stop
            return new_stop
            
        return None
    
    def check_exit(self, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should be closed.
        
        Returns (should_exit, reason)
        """
        if self.active_position is None:
            return False, ""
            
        pos = self.active_position
        
        if pos.direction == Direction.LONG:
            if current_price <= pos.stop_loss:
                return True, "STOP_LOSS"
            if current_price >= pos.take_profit:
                return True, "TAKE_PROFIT"
                
        elif pos.direction == Direction.SHORT:
            if current_price >= pos.stop_loss:
                return True, "STOP_LOSS"
            if current_price <= pos.take_profit:
                return True, "TAKE_PROFIT"
        
        return False, ""
    
    def open_position(self, signal: TradeSignal):
        """Open a new position from signal."""
        self.active_position = PositionState(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            atr_at_entry=signal.atr,
            breakeven_hit=False
        )
        print(f"   📈 Opened {signal.direction.value} @ {signal.entry_price:.2f}")
        print(f"      SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}")
        print(f"      Size: {signal.position_size:.4f}")
    
    def close_position(self, reason: str):
        """Close the active position."""
        if self.active_position:
            print(f"   📉 Closed {self.active_position.direction.value} ({reason})")
            self.active_position = None


# =========================================================================
# TEST
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"STRATEGY: {STRATEGY_NAME}")
    print("=" * 60)
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"EMAs: {EMA_FAST}/{EMA_MID}/{EMA_SLOW}")
    print(f"RSI Period: {RSI_PERIOD}")
    print(f"ATR Period: {ATR_PERIOD}")
    print(f"Risk Per Trade: {RISK_PER_TRADE * 100}%")
    print(f"SL Multiplier: {SL_ATR_MULTIPLIER}x ATR")
    print(f"TP Multiplier: {TP_ATR_MULTIPLIER}x ATR")
    print("=" * 60)
    
    # Create sample data
    np.random.seed(42)
    n = 250  # Need 200+ for EMA_200
    
    # Generate trending price data
    trend = np.linspace(0, 100, n)
    noise = np.random.randn(n) * 10
    close = 90000 + trend + noise
    
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    open_price = close + np.random.randn(n) * 30
    volume = np.random.randint(1000, 5000, n) * 1000
    
    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })
    
    # Test strategy
    strategy = TrendMomentumVolatilityStrategy("BTCUSDT", MarketType.FUTURES)
    
    print(f"\n📊 Testing {strategy.symbol}...")
    trend_data = strategy.analyze_trend(df)
    print(f"   Trend: {trend_data['trend'].value}")
    print(f"   Close: ${trend_data['close']:.2f}")
    print(f"   EMA 50: ${trend_data['ema_50']:.2f}")
    print(f"   EMA 100: ${trend_data['ema_100']:.2f}")
    print(f"   EMA 200: ${trend_data['ema_200']:.2f}")
    
    signal = strategy.generate_signal(df, account_balance=10000)
    if signal:
        print(f"\n   ✅ Signal Generated!")
        print(f"      Type: {signal.signal_type.value}")
        print(f"      Entry: ${signal.entry_price:.2f}")
        print(f"      SL: ${signal.stop_loss:.2f}")
        print(f"      TP: ${signal.take_profit:.2f}")
        print(f"      Size: {signal.position_size:.4f}")
    else:
        print(f"\n   ⚪ No signal generated")
    
    print("\n" + "=" * 60)
