from quant_engine.strategy import Strategy as BaseStrategy
from quant_engine.config import (
    FOREX_RSI_LONG_MIN, FOREX_RSI_LONG_MAX, 
    FOREX_RSI_SHORT_MIN, FOREX_RSI_SHORT_MAX,
    FOREX_MIN_ATR, MAX_SPREAD_PIPS, FOREX_SESSIONS
)
from datetime import datetime
import pytz

class ForexStrategy(BaseStrategy):
    @staticmethod
    def check_entry(symbol, df, supports, resistances):
        """
        FOREX SPECIALIZED LOGIC
        1. Session Filter
        2. Volatility Filter (ATR)
        3. Spread Filter (Simulated)
        4. Widen RSI Bands
        """
        
        # 1. SESSION FILTER
        current_hour = datetime.now(pytz.utc).hour
        if current_hour not in FOREX_SESSIONS:
            # We fail silently or return specific status? 
            # Base returns (Signal, Price, Conf)
            # We return None to indicate "Market Closed/Unsafe"
            return None, None, 0.0

        last = df.iloc[-1]
        
        # 2. ATR VOLATILITY FILTER
        if last['atr'] < FOREX_MIN_ATR:
            # Market too dead. Don't trade.
            return None, None, 0.0
            
        # 3. SPREAD FILTER (Simulated Check)
        # In a real system, we'd pass 'current_spread' as arg.
        # Here we assume spread is acceptable if ATR is healthy, as proxy.
        # (Real implementation needs broker data).
        
        # 4. ADAPTIVE RSI PARAMETERS
        # We need to temporarily "monkey patch" or pass these params.
        # Since BaseStrategy uses global imports, we have to reimplement the Check Logic 
        # OR (cleaner) we modify BaseStrategy to accept params.
        # Given constraint "DO NOT MODIFY CRYPTO LOGIC", strict reimplementation of the 'check' block 
        # using the new constants is safer than touching the Base class signature.
        
        # --- RE-IMPLEMENTATION OF CORE LOGIC WITH FOREX PARAMS ---
        # This duplicates code but ensures 100% isolation as requested.
        
        regime = BaseStrategy.detect_regime(last)
        price = last['close']
        atr = last['atr']
        confidence = 0.5 
        
        # === LONG ===
        if regime == "BULLISH":
            if last['ema_50_slope'] > 0: confidence += 0.1
            valid_supports = supports[supports < price]
            if len(valid_supports) > 0:
                nearest_supp = valid_supports.max()
                dist_to_supp = price - nearest_supp
                if dist_to_supp <= (0.3 * atr): confidence += 0.2
                if dist_to_supp <= (0.5 * atr):
                    # FOREX RSI CHECK
                    if FOREX_RSI_LONG_MIN <= last['rsi'] <= FOREX_RSI_LONG_MAX:
                         dist = abs(last['rsi'] - 45)
                         score = max(0, 0.2 - (dist * 0.02))
                         confidence += score
                         
                         limit = last['ema_50'] - (1 * atr)
                         if price >= limit:
                             if last['close'] > last['open']:
                                 return "LONG", nearest_supp, min(confidence, 1.0)

        # === SHORT ===
        elif regime == "BEARISH":
            if last['ema_50_slope'] < 0: confidence += 0.1
            valid_res = resistances[resistances > price]
            if len(valid_res) > 0:
                nearest_res = valid_res.min()
                dist_to_res = nearest_res - price
                if dist_to_res <= (0.3 * atr): confidence += 0.2
                if dist_to_res <= (0.5 * atr):
                    # FOREX RSI CHECK
                    if FOREX_RSI_SHORT_MIN <= last['rsi'] <= FOREX_RSI_SHORT_MAX:
                        dist = abs(last['rsi'] - 60)
                        score = max(0, 0.2 - (dist * 0.02))
                        confidence += score
                        
                        limit = last['ema_50'] + (1 * atr)
                        if price <= limit:
                            if last['close'] < last['open']:
                                return "SHORT", nearest_res, min(confidence, 1.0)
                                
        return None, None, 0.0
