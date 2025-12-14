import pandas as pd
import numpy as np
from quant_engine.config import (
    RSI_LONG_MIN, RSI_LONG_MAX, RSI_SHORT_MIN, RSI_SHORT_MAX,
    EMA_FAST, EMA_SLOW
)

class Strategy:
    @staticmethod
    def calculate_indicators(df):
        # EMA
        df['ema_50'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
        
        # ATR 14
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Volatility Filter (ATR vs rolling ATR mean)
        df['avg_atr'] = df['atr'].rolling(window=50).mean()
        
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume Mean
        df['vol_mean'] = df['volume'].rolling(20).mean()
        
        # Slope of EMA 50
        df['ema_50_slope'] = df['ema_50'].diff(3)
        
        return df

    @staticmethod
    def detect_regime(row):
        """
        Bullish: Price > 200 EMA & EMA Slope > 0
        Bearish: Price < 200 EMA & EMA Slope < 0
        Range: Otherwise
        """
        price = row['close']
        ema_200 = row['ema_200']
        slope = row['ema_50_slope']
        
        # Basic filter for undefined slope
        if pd.isna(slope): return "NEUTRAL"

        if price > ema_200 and slope > 0:
            return "BULLISH"
        elif price < ema_200 and slope < 0:
            return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def find_sr_zones(df, window=5):
        df['is_high'] = df['high'] == df['high'].rolling(window=window*2+1, center=True).max()
        df['is_low'] = df['low'] == df['low'].rolling(window=window*2+1, center=True).min()
        
        supports = df[df['is_low']]['low'].values
        resistances = df[df['is_high']]['high'].values
        return supports, resistances

    @staticmethod
    def check_entry(symbol, df, supports, resistances):
        """
        Returns: 'LONG', 'SHORT', or None
        Also returns: trigger_price, confidence_score
        """
        last = df.iloc[-1]
        
        # 0. Volatility Filter
        if last['atr'] > (2 * last['avg_atr']):
            return None, None, 0.0
            
        regime = Strategy.detect_regime(last)
        price = last['close']
        atr = last['atr']
        
        confidence = 0.5 # Base Confidence
        
        # === LONG CONDITIONS ===
        if regime == "BULLISH":
            # Bonus: Strong Trend
            if last['ema_50_slope'] > 0: confidence += 0.1
            
            # 1. Price Pullback to Support
            valid_supports = supports[supports < price]
            if len(valid_supports) > 0:
                nearest_supp = valid_supports.max()
                dist_to_supp = price - nearest_supp
                
                # Perfect touch bonus (within 0.3 ATR)
                if dist_to_supp <= (0.3 * atr): confidence += 0.2
                
                if dist_to_supp <= (0.5 * atr):
                    # 2. Strict RSI (40-50)
                    # Ideal RSI for pullback buy is ~45.
                    if RSI_LONG_MIN <= last['rsi'] <= RSI_LONG_MAX:
                        dist_from_ideal = abs(last['rsi'] - 45)
                        rsi_score = max(0, 0.2 - (dist_from_ideal * 0.02)) # Max 0.2 bonus
                        confidence += rsi_score
                        
                        # 3. Price vs 50 EMA: Price >= 50EMA - 1ATR
                        limit = last['ema_50'] - (1 * atr)
                        if price >= limit:
                             if last['close'] > last['open']: # Green Candle
                                 return "LONG", nearest_supp, min(confidence, 1.0)

        # === SHORT CONDITIONS ===
        elif regime == "BEARISH":
            if last['ema_50_slope'] < 0: confidence += 0.1
            
            # 1. Price Rally to Resistance
            valid_res = resistances[resistances > price]
            if len(valid_res) > 0:
                nearest_res = valid_res.min()
                dist_to_res = nearest_res - price
                
                if dist_to_res <= (0.3 * atr): confidence += 0.2
                
                if dist_to_res <= (0.5 * atr):
                    # 2. Strict RSI (55-65)
                    # Ideal RSI for short is ~60
                    if RSI_SHORT_MIN <= last['rsi'] <= RSI_SHORT_MAX:
                        dist_from_ideal = abs(last['rsi'] - 60)
                        rsi_score = max(0, 0.2 - (dist_from_ideal * 0.02))
                        confidence += rsi_score
                        
                        # 3. Price vs 50 EMA: Price <= 50EMA + 1ATR
                        limit = last['ema_50'] + (1 * atr)
                        if price <= limit:
                            if last['close'] < last['open']: # Red Candle
                                return "SHORT", nearest_res, min(confidence, 1.0)

        return None, None, 0.0
