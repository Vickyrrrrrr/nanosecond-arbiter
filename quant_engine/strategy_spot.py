from quant_engine.strategy import Strategy as BaseStrategy
from quant_engine.config import RSI_LONG_MIN, RSI_LONG_MAX

class SpotStrategy(BaseStrategy):
    @staticmethod
    def check_entry(symbol, df, supports, resistances):
        """
        SPOT = LONG ONLY
        Delegates to BaseStrategy (User's Strategy) logic
        """
        signal, price, confidence = BaseStrategy.check_entry(symbol, df, supports, resistances)
        
        if signal == "LONG":
            return signal, price, confidence
            
        return None, None, 0.0
