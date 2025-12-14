from quant_engine.strategy import Strategy as BaseStrategy
from quant_engine.config import RSI_SHORT_MIN, RSI_SHORT_MAX

class FuturesStrategy(BaseStrategy):
    @staticmethod
    def check_entry(symbol, df, supports, resistances):
        """
        FUTURES = LONG + SHORT
        Delegates to BaseStrategy (User's Strategy) logic
        """
        # Fully integrate user's strategy for Futures
        return BaseStrategy.check_entry(symbol, df, supports, resistances)
