"""
Pure Price Action Breakout Strategy
====================================
A clean, rule-based crypto trading strategy using ONLY price action,
structure, volatility, and mathematics.

NO indicators (RSI, MACD, EMA, VWAP).
NO prediction.
ONLY price, structure, range, volatility.

Supports:
- Spot (Long only)
- Futures (Long + Short)
- 5m primary, 15m confirmation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketType(Enum):
    SPOT = "SPOT"
    FUTURES = "FUTURES"


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalType(Enum):
    BULLISH_BREAKOUT = "BULLISH_BREAKOUT"
    BEARISH_BREAKOUT = "BEARISH_BREAKOUT"
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
    breakout_level: float
    candle_range: float
    avg_range: float
    timestamp: int


@dataclass
class MarketStructure:
    """Current market structure based on price action."""
    resistance: float          # Recent swing high
    support: float             # Recent swing low
    current_close: float
    current_open: float
    current_high: float
    current_low: float
    candle_body: float         # |close - open|
    candle_range: float        # high - low
    avg_range: float           # Average range of recent candles
    is_bullish_candle: bool    # close > open
    volatility_expanded: bool  # Current range > average range


class PriceActionStrategy:
    """
    Pure Price Action Breakout Strategy.
    
    Uses ONLY:
    - Swing highs and lows (structure)
    - Candle range (volatility)
    - Price closes (confirmation)
    
    NO indicators allowed.
    """
    
    # Configuration
    LOOKBACK_STRUCTURE = 20     # Candles to find swing points
    LOOKBACK_VOLATILITY = 10   # Candles for average range
    MIN_STRUCTURE_HOLD = 3     # Candles structure must hold
    TIME_EXIT_CANDLES = 8      # Exit if no continuation
    
    # Risk Parameters (STRICT)
    TOTAL_CAPITAL = 10000.0    # Fixed Base Capital
    MAX_TRADE_CAPITAL = 2500.0 # Hard Cap per trade
    RISK_PERCENT = 0.01        # 1% of Total Capital ($100)
    MAX_WICK_RATIO = 0.40      # Max allowed wick size relative to range
    
    TP_R_MULTIPLE = 1.0        # Take profit at 1R
    TRAILING_START_R = 1.5     # Start trailing at 1.5R
    MAX_LEVERAGE = 5           # Conservative leverage limit
    
    def __init__(self, symbol: str, market_type: MarketType = MarketType.SPOT):
        self.symbol = symbol
        self.market_type = market_type
        
        # Cooldown state
        self.cooldown_active = False
        self.cooldown_candles = 0 # Number of signals to skip
        
    # =========================================================================
    # STRUCTURE DETECTION (Pure Price Action)
    # =========================================================================
    
    @staticmethod
    def find_swing_high(df: pd.DataFrame, lookback: int = 20) -> float:
        """
        Find the highest high in recent candles (resistance).
        Only counts if it's been tested/held for multiple candles.
        """
        if len(df) < lookback:
            return df['high'].max()
        
        recent = df.tail(lookback)
        return recent['high'].max()
    
    @staticmethod
    def find_swing_low(df: pd.DataFrame, lookback: int = 20) -> float:
        """
        Find the lowest low in recent candles (support).
        """
        if len(df) < lookback:
            return df['low'].min()
        
        recent = df.tail(lookback)
        return recent['low'].min()
    
    @staticmethod
    def calculate_average_range(df: pd.DataFrame, lookback: int = 10) -> float:
        """Calculate average candle range (volatility measure)."""
        if len(df) < lookback:
            lookback = len(df)
        
        ranges = df['high'].tail(lookback) - df['low'].tail(lookback)
        return ranges.mean()
    
    @staticmethod
    def is_structure_holding(df: pd.DataFrame, level: float, is_resistance: bool, min_candles: int = 3) -> bool:
        """
        Check if a structure level has held for minimum candles.
        
        For resistance: price must have touched but not closed above
        For support: price must have touched but not closed below
        """
        if len(df) < min_candles:
            return False
        
        recent = df.tail(min_candles)
        
        if is_resistance:
            # Check if high touched but close stayed below
            touches = (recent['high'] >= level * 0.998).sum()  # Within 0.2%
            breaks = (recent['close'] > level).sum()
            return touches >= 1 and breaks == 0
        else:
            # Check if low touched but close stayed above  
            touches = (recent['low'] <= level * 1.002).sum()
            breaks = (recent['close'] < level).sum()
            return touches >= 1 and breaks == 0
    
    # =========================================================================
    # MARKET STRUCTURE ANALYSIS
    # =========================================================================
    
    def analyze_structure(self, df: pd.DataFrame) -> MarketStructure:
        """
        Analyze current market structure using only price.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            MarketStructure with key levels and volatility
        """
        if len(df) < self.LOOKBACK_STRUCTURE:
            raise ValueError(f"Need at least {self.LOOKBACK_STRUCTURE} candles")
        
        # Current candle (last closed)
        current = df.iloc[-1]
        
        # Find structure levels (exclude current candle)
        resistance = self.find_swing_high(df.iloc[:-1], self.LOOKBACK_STRUCTURE)
        support = self.find_swing_low(df.iloc[:-1], self.LOOKBACK_STRUCTURE)
        
        # Calculate volatility
        avg_range = self.calculate_average_range(df.iloc[:-1], self.LOOKBACK_VOLATILITY)
        current_range = current['high'] - current['low']
        
        # Candle properties
        candle_body = abs(current['close'] - current['open'])
        is_bullish = current['close'] > current['open']
        
        # Volatility expansion check
        volatility_expanded = current_range > avg_range
        
        return MarketStructure(
            resistance=resistance,
            support=support,
            current_close=current['close'],
            current_open=current['open'],
            current_high=current['high'],
            current_low=current['low'],
            candle_body=candle_body,
            candle_range=current_range,
            avg_range=avg_range,
            is_bullish_candle=is_bullish,
            volatility_expanded=volatility_expanded
        )
    
    # =========================================================================
    # BREAKOUT DETECTION
    # =========================================================================
    
    def check_bullish_breakout(self, structure: MarketStructure) -> Tuple[bool, str]:
        """
        Check for bullish breakout.
        
        Conditions:
        1. Price CLOSES above resistance (not just wick)
        2. Candle body closes outside range
        3. Volatility expansion present
        4. Upper wick not too large (no rejection)
        
        Returns:
            Tuple of (is_valid, reason)
        """
        reasons = []
        
        # 1. Close above resistance
        if structure.current_close <= structure.resistance:
            return False, "Close not above resistance"
        reasons.append("Close > Resistance")
        
        # 2. Body must close outside
        body_top = max(structure.current_close, structure.current_open)
        if body_top <= structure.resistance:
            return False, "Only wick break, body inside"
        reasons.append("Body outside range")
        
        # 3. Volatility expansion
        if not structure.volatility_expanded:
            return False, "No volatility expansion"
        reasons.append("Volatility expanded")
        
        # 4. Must be bullish candle
        if not structure.is_bullish_candle:
            return False, "Not a bullish candle"
        reasons.append("Bullish candle")
        
        # 5. Rejection Check (Upper wick must be small)
        upper_wick = structure.current_high - max(structure.current_close, structure.current_open)
        wick_ratio = upper_wick / structure.candle_range if structure.candle_range > 0 else 0
        
        if wick_ratio > self.MAX_WICK_RATIO:
            return False, f"Rejection Wick too large ({wick_ratio:.2f})"
        reasons.append("Wick OK")
        
        return True, " | ".join(reasons)
    
    def check_bearish_breakout(self, structure: MarketStructure) -> Tuple[bool, str]:
        """
        Check for bearish breakout.
        
        Conditions:
        1. Price CLOSES below support (not just wick)
        2. Candle body closes outside range
        3. Volatility expansion present
        4. Lower wick not too large (no rejection)
        
        Returns:
            Tuple of (is_valid, reason)
        """
        reasons = []
        
        # 1. Close below support
        if structure.current_close >= structure.support:
            return False, "Close not below support"
        reasons.append("Close < Support")
        
        # 2. Body must close outside
        body_bottom = min(structure.current_close, structure.current_open)
        if body_bottom >= structure.support:
            return False, "Only wick break, body inside"
        reasons.append("Body outside range")
        
        # 3. Volatility expansion
        if not structure.volatility_expanded:
            return False, "No volatility expansion"
        reasons.append("Volatility expanded")
        
        # 4. Must be bearish candle
        if structure.is_bullish_candle:
            return False, "Not a bearish candle"
        reasons.append("Bearish candle")
        
        # 5. Rejection Check (Lower wick must be small)
        lower_wick = min(structure.current_close, structure.current_open) - structure.current_low
        wick_ratio = lower_wick / structure.candle_range if structure.candle_range > 0 else 0
        
        if wick_ratio > self.MAX_WICK_RATIO:
            return False, f"Rejection Wick too large ({wick_ratio:.2f})"
        reasons.append("Wick OK")
        
        return True, " | ".join(reasons)
    
    # =========================================================================
    # 15M CONFIRMATION
    # =========================================================================
    
    def get_15m_bias(self, df_15m: pd.DataFrame) -> Direction:
        """
        Get 15m structure bias to filter trades.
        
        Returns:
            LONG if structure bullish, SHORT if bearish, NEUTRAL otherwise
        """
        if len(df_15m) < 10:
            return Direction.NEUTRAL
        
        structure = self.analyze_structure(df_15m)
        
        # Simple bias: where is price relative to range?
        range_size = structure.resistance - structure.support
        mid = structure.support + (range_size / 2)
        
        if structure.current_close > mid + (range_size * 0.2):
            return Direction.LONG
        elif structure.current_close < mid - (range_size * 0.2):
            return Direction.SHORT
        else:
            return Direction.NEUTRAL
    
    # =========================================================================
    # SIGNAL GENERATION
    # =========================================================================
    
    def generate_signal(
        self, 
        df_5m: pd.DataFrame, 
        df_15m: pd.DataFrame = None,
        timestamp: int = 0
    ) -> Optional[TradeSignal]:
        """
        Generate trading signal from price data.
        
        Args:
            df_5m: 5-minute OHLCV data
            df_15m: 15-minute OHLCV data for confirmation
            timestamp: Current timestamp
            
        Returns:
            TradeSignal if valid breakout, None otherwise
        """
        # Check cooldown
        if self.cooldown_active:
            self.cooldown_candles -= 1
            if self.cooldown_candles <= 0:
                self.cooldown_active = False
            else:
                return None
        
        # Analyze 5m structure
        try:
            structure = self.analyze_structure(df_5m)
        except ValueError:
            return None
        
        # Get 15m bias if available
        bias_15m = Direction.NEUTRAL
        if df_15m is not None and len(df_15m) >= 10:
            bias_15m = self.get_15m_bias(df_15m)
        
        # Check for bullish breakout
        is_bullish, bullish_reason = self.check_bullish_breakout(structure)
        
        if is_bullish:
            # Confirm 15m is not bearish
            if bias_15m == Direction.SHORT:
                print(f"   🚫 {self.symbol}: Bullish Breakout rejected by 15m Bearish Structure")
                return None  # 15m bearish, skip long
            
            entry = structure.current_close
            sl = structure.resistance - (structure.avg_range * 0.5)  # Below breakout
            risk = entry - sl
            tp = entry + risk  # 1R
            
            return TradeSignal(
                symbol=self.symbol,
                timeframe="5m",
                signal_type=SignalType.BULLISH_BREAKOUT,
                direction=Direction.LONG,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                breakout_level=structure.resistance,
                candle_range=structure.candle_range,
                avg_range=structure.avg_range,
                timestamp=timestamp
            )
        else:
             print(f"   ⚪ {self.symbol} Bullish Logic: {bullish_reason}")
        
        # Check for bearish breakout (Futures only)
        if self.market_type == MarketType.FUTURES:
            is_bearish, bearish_reason = self.check_bearish_breakout(structure)
            
            if is_bearish:
                # Confirm 15m is not bullish
                if bias_15m == Direction.LONG:
                    print(f"   🚫 {self.symbol}: Bearish Breakout rejected by 15m Bullish Structure")
                    return None  # 15m bullish, skip short
                
                entry = structure.current_close
                sl = structure.support + (structure.avg_range * 0.5)  # Above breakout
                risk = sl - entry
                tp = entry - risk  # 1R
                
                return TradeSignal(
                    symbol=self.symbol,
                    timeframe="5m",
                    signal_type=SignalType.BEARISH_BREAKOUT,
                    direction=Direction.SHORT,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    breakout_level=structure.support,
                    candle_range=structure.candle_range,
                    avg_range=structure.avg_range,
                    timestamp=timestamp
                )
            else:
                 print(f"   ⚪ {self.symbol} Bearish Logic: {bearish_reason}")
        
        return None
    
    # =========================================================================
    # POSITION SIZING (STRICT)
    # =========================================================================
    
    def calculate_position_size(self, current_balance: float, entry: float, stop_loss: float) -> float:
        """
        Calculate strict position size.
        
        Formula:
        1. Risk-Based: (Total Capital * 1%) / Distance
        2. Cap-Based: Max Trade Capital / Entry
        3. Final: MIN(Risk-Based, Cap-Based)
        """
        # 1. Risk-Based Size ($100 max loss)
        risk_amount = self.TOTAL_CAPITAL * self.RISK_PERCENT
        dist = abs(entry - stop_loss)
        
        if dist == 0: return 0
        
        qty_risk = risk_amount / dist
        
        # 2. Capital-Based Size ($2500 max val)
        # For Futures: This is NOT leverage based, this is Notional Value Cap.
        # Max Position Value = $2500
        qty_cap = self.MAX_TRADE_CAPITAL / entry
        
        # 3. Final Strict Size
        final_qty = min(qty_risk, qty_cap)
        
        return final_qty
    
    # =========================================================================
    # COOLDOWN MANAGEMENT
    # =========================================================================
    
    def activate_cooldown(self, candles: int = 5):
        """Activate cooldown after a loss."""
        self.cooldown_active = True
        self.cooldown_candles = candles
