"""
Pure Mathematical Indian F&O Breakout System
=============================================
Intraday trading system for NIFTY 50 & BANK NIFTY.

SEBI compliant - Intraday only, no overnight positions.
NO indicators - Only price, structure, volatility, time.

Trading Window:
- Start: 09:20 IST
- Stop entries: 14:45 IST
- Mandatory exit: 15:20 IST
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time
import pytz


IST = pytz.timezone('Asia/Kolkata')


class InstrumentType(Enum):
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class TradeType(Enum):
    BREAKOUT = "BREAKOUT"
    BREAKDOWN = "BREAKDOWN"
    FORCED_DAILY = "FORCED_DAILY"


class SignalType(Enum):
    BULLISH_BREAKOUT = "BULLISH_BREAKOUT"
    BEARISH_BREAKDOWN = "BEARISH_BREAKDOWN"
    FORCED_TRADE = "FORCED_TRADE"
    NO_SIGNAL = "NO_SIGNAL"


@dataclass
class IndianFOSignal:
    """Trade signal for Indian F&O."""
    symbol: str  # NIFTY or BANKNIFTY
    signal_type: SignalType
    trade_type: TradeType
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    breakout_level: float
    instrument: InstrumentType
    option_type: str  # CALL or PUT (if options)
    timestamp: datetime


@dataclass
class OpeningRange:
    """Opening range structure (09:15-09:45 IST)."""
    range_high: float
    range_low: float
    range_size: float
    is_complete: bool


@dataclass
class DayStructure:
    """Daily price structure."""
    day_high: float
    day_low: float
    opening_range: OpeningRange
    avg_range_10: float  # Average candle range of last 10


class IndianFOStrategy:
    """
    Pure Mathematical Indian F&O Breakout System.
    
    ONLY for NIFTY 50 and BANK NIFTY.
    NO indicators - price, structure, volatility, time only.
    """
    
    # Trading Window (IST)
    SCAN_START = time(9, 20)
    ENTRY_STOP = time(14, 45)
    MANDATORY_EXIT = time(15, 20)
    FORCED_TRADE_TIME = time(11, 30)
    
    # Opening Range Window
    OR_START = time(9, 15)
    OR_END = time(9, 45)
    
    # Risk Parameters
    RISK_PERCENT = 0.01  # 1% per trade
    MAX_TRADES_PER_DAY = 3
    MAX_LOSS_PERCENT = 0.02  # 2% max daily loss
    OPTION_SL_PERCENT = 0.35  # 35% premium SL
    MAX_WICK_RATIO = 0.40      # Max allowed wick size relative to range (Strict Wick Filter)
    
    def __init__(self, symbol: str):
        """
        Initialize strategy for a symbol.
        
        Args:
            symbol: NIFTY or BANKNIFTY
        """
        if symbol not in ["NIFTY", "BANKNIFTY"]:
            raise ValueError("Symbol must be NIFTY or BANKNIFTY")
        
        self.symbol = symbol
        
        # Daily state
        self.opening_range: Optional[OpeningRange] = None
        self.day_high: float = 0
        self.day_low: float = float('inf')
        self.trades_today: int = 0
        self.losses_today: int = 0
        self.daily_pnl: float = 0
        self.forced_trade_used: bool = False
        
        # Cooldown state
        self.cooldown_active: bool = False
        self.cooldown_signals: int = 0
        
    def activate_cooldown(self, signals_to_skip: int = 2):
        """Activate cooldown to skip next N valid signals."""
        self.cooldown_active = True
        self.cooldown_signals = signals_to_skip
        
    # =========================================================================
    # TIME CHECKS
    # =========================================================================
    
    def is_market_open(self) -> bool:
        """Check if market is open."""
        now = datetime.now(IST).time()
        return time(9, 15) <= now <= time(15, 30)
    
    def can_enter_new_trade(self) -> bool:
        """Check if new entries are allowed."""
        now = datetime.now(IST).time()
        return self.SCAN_START <= now <= self.ENTRY_STOP
    
    def should_force_exit(self) -> bool:
        """Check if mandatory exit time reached."""
        now = datetime.now(IST).time()
        return now >= self.MANDATORY_EXIT
    
    def is_forced_trade_time(self) -> bool:
        """Check if forced trade window is active (after 11:30)."""
        now = datetime.now(IST).time()
        return now >= self.FORCED_TRADE_TIME
    
    def is_opening_range_complete(self) -> bool:
        """Check if opening range period is over."""
        now = datetime.now(IST).time()
        return now > self.OR_END
    
    # =========================================================================
    # STRUCTURE DETECTION
    # =========================================================================
    
    def calculate_opening_range(self, df: pd.DataFrame) -> OpeningRange:
        """
        Calculate opening range from 09:15-09:45 IST candles.
        
        Args:
            df: Intraday OHLCV data with IST timestamps
        """
        if self.opening_range and self.opening_range.is_complete:
            return self.opening_range
        
        # Filter for opening range period
        or_candles = df[
            (df.index.time >= self.OR_START) & 
            (df.index.time <= self.OR_END)
        ]
        
        if or_candles.empty:
            return OpeningRange(0, 0, 0, False)
        
        range_high = or_candles['high'].max()
        range_low = or_candles['low'].min()
        range_size = range_high - range_low
        
        is_complete = self.is_opening_range_complete()
        
        self.opening_range = OpeningRange(
            range_high=range_high,
            range_low=range_low,
            range_size=range_size,
            is_complete=is_complete
        )
        
        return self.opening_range
    
    def update_day_structure(self, df: pd.DataFrame) -> DayStructure:
        """Update daily high/low and structure."""
        today = datetime.now(IST).date()
        today_data = df[df.index.date == today]
        
        if not today_data.empty:
            self.day_high = max(self.day_high, today_data['high'].max())
            self.day_low = min(self.day_low, today_data['low'].min())
        
        # Calculate average range
        ranges = df['high'].tail(10) - df['low'].tail(10)
        avg_range = ranges.mean()
        
        return DayStructure(
            day_high=self.day_high,
            day_low=self.day_low,
            opening_range=self.opening_range or OpeningRange(0, 0, 0, False),
            avg_range_10=avg_range
        )
    
    # =========================================================================
    # BREAKOUT DETECTION
    # =========================================================================
    
    def check_breakout(self, df: pd.DataFrame, structure: DayStructure) -> Tuple[bool, str]:
        """
        Check for bullish breakout conditions.
        
        Conditions (ALL must be TRUE):
        1. 5m candle CLOSES above Range High
        2. Candle BODY breaks level (not just wick)
        3. Volatility expansion (range > avg)
        """
        if not structure.opening_range.is_complete:
            return False, "Opening range not complete"
        
        current = df.iloc[-1]
        level = structure.opening_range.range_high
        
        # 1. Close above range high
        if current['close'] <= level:
            return False, "Close not above range high"
        
        # 2. Body must break (not just wick)
        body_top = max(current['close'], current['open'])
        if body_top <= level:
            return False, "Only wick break, body inside"
        
        # 3. Volatility expansion
        current_range = current['high'] - current['low']
        if current_range <= structure.avg_range_10:
            return False, "No volatility expansion"
            
        # 4. Rejection Check (Upper wick must be small)
        upper_wick = current['high'] - max(current['close'], current['open'])
        wick_ratio = upper_wick / current_range if current_range > 0 else 0
        
        if wick_ratio > self.MAX_WICK_RATIO:
            return False, f"Rejection Wick too large ({wick_ratio:.2f})"
        
        return True, "Valid breakout"
    
    def check_breakdown(self, df: pd.DataFrame, structure: DayStructure) -> Tuple[bool, str]:
        """
        Check for bearish breakdown conditions.
        
        Conditions (ALL must be TRUE):
        1. 5m candle CLOSES below Range Low
        2. Candle BODY breaks level
        3. Volatility expansion
        4. Lower wick not too large (no rejection)
        """
        if not structure.opening_range.is_complete:
            return False, "Opening range not complete"
        
        current = df.iloc[-1]
        level = structure.opening_range.range_low
        
        # 1. Close below range low
        if current['close'] >= level:
            return False, "Close not below range low"
        
        # 2. Body must break
        body_bottom = min(current['close'], current['open'])
        if body_bottom >= level:
            return False, "Only wick break, body inside"
        
        # 3. Volatility expansion
        current_range = current['high'] - current['low']
        if current_range <= structure.avg_range_10:
            return False, "No volatility expansion"
            
        # 4. Rejection Check (Lower wick must be small)
        lower_wick = min(current['close'], current['open']) - current['low']
        wick_ratio = lower_wick / current_range if current_range > 0 else 0
        
        if wick_ratio > self.MAX_WICK_RATIO:
            return False, f"Rejection Wick too large ({wick_ratio:.2f})"
        
        return True, "Valid breakdown"
    
    def check_forced_trade(self, df: pd.DataFrame, structure: DayStructure) -> Optional[Tuple[Direction, float]]:
        """
        Check for forced daily trade conditions.
        
        Used when no breakout/breakdown occurs by 11:30 IST.
        Identifies strongest rejection level and enters on confirmation.
        """
        if not self.is_forced_trade_time() or self.forced_trade_used:
            return None
        
        if self.trades_today > 0:
            return None  # Already traded today
        
        recent = df.tail(20)
        if len(recent) < 10:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Look for strong rejection candle
        current_range = current['high'] - current['low']
        current_body = abs(current['close'] - current['open'])
        
        # Strong bullish rejection from support
        if (current['close'] > current['open'] and  # Bullish candle
            current_body > structure.avg_range_10 * 0.6 and  # Strong body
            prev['close'] < prev['open']):  # Follow through
            return Direction.LONG, structure.opening_range.range_low
        
        # Strong bearish rejection from resistance
        if (current['close'] < current['open'] and  # Bearish candle
            current_body > structure.avg_range_10 * 0.6 and  # Strong body
            prev['close'] > prev['open']):  # Follow through
            return Direction.SHORT, structure.opening_range.range_high
        
        return None
    
    # =========================================================================
    # 15M CONFIRMATION
    # =========================================================================
    
    def get_15m_structure(self, df_15m: pd.DataFrame) -> Direction:
        """Get 15m timeframe structure for confirmation."""
        if len(df_15m) < 5:
            return Direction.NEUTRAL
        
        recent = df_15m.tail(5)
        closes = recent['close'].values
        
        # Simple trend check
        if closes[-1] > closes[0] and closes[-1] > recent['open'].iloc[-1]:
            return Direction.LONG
        elif closes[-1] < closes[0] and closes[-1] < recent['open'].iloc[-1]:
            return Direction.SHORT
        
        return Direction.NEUTRAL
    
    # =========================================================================
    # SIGNAL GENERATION
    # =========================================================================
    
    def generate_signal(
        self,
        df_5m: pd.DataFrame,
        df_15m: pd.DataFrame = None
    ) -> Optional[IndianFOSignal]:
        """
        Generate trading signal for NIFTY/BANKNIFTY.
        
        Args:
            df_5m: 5-minute OHLCV data
            df_15m: 15-minute OHLCV data
            
        Returns:
            IndianFOSignal if valid setup, None otherwise
        """
        # Check if we can trade
        if not self.can_enter_new_trade():
            return None
        
        if self.trades_today >= self.MAX_TRADES_PER_DAY:
            return None
        
        if self.losses_today >= 2:  # Max 2 losing trades
            return None
        
        # Check Cooldown (Skip Signals)
        # Note: If cooldown is active, we check if we have a valid signal, then skip it and decrement counter.
        # This is more precise than time-based cooldown.
        
        # Update structure
        self.calculate_opening_range(df_5m)
        structure = self.update_day_structure(df_5m)
        
        if not structure.opening_range.is_complete:
            return None
        
        # Get 15m confirmation
        bias_15m = Direction.NEUTRAL
        if df_15m is not None:
            bias_15m = self.get_15m_structure(df_15m)
        
        current = df_5m.iloc[-1]
        entry = current['close']
        
        # Check for breakout
        is_breakout, _ = self.check_breakout(df_5m, structure)
        if is_breakout and bias_15m != Direction.SHORT:
            if self.cooldown_active:
                self.cooldown_signals -= 1
                print(f"   🧊 Cooldown: Skipping Bullish Signal ({self.cooldown_signals} remaining)")
                if self.cooldown_signals <= 0:
                    self.cooldown_active = False
                return None

            sl = structure.opening_range.range_high - (structure.avg_range_10 * 0.5)
            risk = entry - sl
            tp = entry + risk  # 1R
            
            return IndianFOSignal(
                symbol=self.symbol,
                signal_type=SignalType.BULLISH_BREAKOUT,
                trade_type=TradeType.BREAKOUT,
                direction=Direction.LONG,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                breakout_level=structure.opening_range.range_high,
                instrument=InstrumentType.FUTURES,
                option_type="CALL",
                timestamp=datetime.now(IST)
            )
        
        # Check for breakdown
        is_breakdown, _ = self.check_breakdown(df_5m, structure)
        if is_breakdown and bias_15m != Direction.LONG:
            if self.cooldown_active:
                self.cooldown_signals -= 1
                print(f"   🧊 Cooldown: Skipping Bearish Signal ({self.cooldown_signals} remaining)")
                if self.cooldown_signals <= 0:
                    self.cooldown_active = False
                return None

            sl = structure.opening_range.range_low + (structure.avg_range_10 * 0.5)
            risk = sl - entry
            tp = entry - risk  # 1R
            
            return IndianFOSignal(
                symbol=self.symbol,
                signal_type=SignalType.BEARISH_BREAKDOWN,
                trade_type=TradeType.BREAKDOWN,
                direction=Direction.SHORT,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                breakout_level=structure.opening_range.range_low,
                instrument=InstrumentType.FUTURES,
                option_type="PUT",
                timestamp=datetime.now(IST)
            )
        
        # Forced Trade logic (11:30 Check)
        forced_trade = self.check_forced_trade(df_5m, structure)
        if forced_trade:
            direction, level = forced_trade
            
            if self.cooldown_active:
                 # Also skip forced trades if in penalty box
                self.cooldown_signals -= 1
                print(f"   🧊 Cooldown: Skipping Forced Signal ({self.cooldown_signals} remaining)")
                if self.cooldown_signals <= 0:
                    self.cooldown_active = False
                return None

            sl_dist = structure.avg_range_10 * 0.5
            if direction == Direction.LONG:
                sl = entry - sl_dist
                tp = entry + sl_dist * 2 # 1:2 for reversal
            else:
                sl = entry + sl_dist
                tp = entry - sl_dist * 2
            
            self.forced_trade_used = True
            
            return IndianFOSignal(
                symbol=self.symbol,
                signal_type=SignalType.FORCED_TRADE,
                trade_type=TradeType.FORCED_DAILY,
                direction=direction,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                breakout_level=level,
                instrument=InstrumentType.FUTURES,
                option_type="CALL" if direction == Direction.LONG else "PUT",
                timestamp=datetime.now(IST)
            )
        
        return None
        
        return None
    
    # =========================================================================
    # POSITION SIZING
    # =========================================================================
    
    def calculate_lot_size(self, capital: float, entry: float, stop_loss: float) -> int:
        """
        Calculate lot size based on risk.
        
        NIFTY lot = 50
        BANKNIFTY lot = 25
        """
        lot_size = 50 if self.symbol == "NIFTY" else 25
        
        risk_amount = capital * self.RISK_PERCENT
        risk_per_unit = abs(entry - stop_loss)
        
        if risk_per_unit == 0:
            return 0
        
        units = risk_amount / risk_per_unit
        lots = int(units / lot_size)
        
        return max(1, lots)  # Minimum 1 lot
    
    # =========================================================================
    # DAILY RESET
    # =========================================================================
    
    def reset_daily_state(self):
        """Reset all daily tracking variables."""
        self.opening_range = None
        self.day_high = 0
        self.day_low = float('inf')
        self.trades_today = 0
        self.losses_today = 0
        self.daily_pnl = 0
        self.forced_trade_used = False


# =========================================================================
# TEST
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("INDIAN F&O BREAKOUT SYSTEM")
    print("NIFTY & BANKNIFTY | NO INDICATORS | INTRADAY ONLY")
    print("=" * 60)
    
    # Create sample data
    np.random.seed(42)
    n = 50
    
    close = 25000 + np.cumsum(np.random.randn(n) * 20)
    high = close + np.abs(np.random.randn(n) * 10)
    low = close - np.abs(np.random.randn(n) * 10)
    open_price = close + np.random.randn(n) * 5
    volume = np.random.randint(1000000, 5000000, n)
    
    # Create index with IST times
    times = pd.date_range(
        start='2024-12-16 09:15:00',
        periods=n,
        freq='5min',
        tz=IST
    )
    
    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=times)
    
    # Test strategy
    strategy = IndianFOStrategy("NIFTY")
    
    print(f"\n📊 Testing NIFTY strategy...")
    print(f"   Market Open: {strategy.is_market_open()}")
    print(f"   Can Trade: {strategy.can_enter_new_trade()}")
    
    # Calculate opening range
    or_struct = strategy.calculate_opening_range(df)
    print(f"\n   Opening Range:")
    print(f"     High: ₹{or_struct.range_high:.2f}")
    print(f"     Low: ₹{or_struct.range_low:.2f}")
    print(f"     Size: ₹{or_struct.range_size:.2f}")
    print(f"     Complete: {or_struct.is_complete}")
    
    print("\n" + "=" * 60)
