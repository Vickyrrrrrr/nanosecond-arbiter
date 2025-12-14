import pandas as pd
from quant_engine.config import RISK_SPOT, RISK_FUTURES, MAX_DAILY_LOSS, LEVERAGE_MAP

class RiskManager:
    def __init__(self, equity=10000.0, account_type="SPOT"):
        self.equity = equity
        self.start_equity = equity
        self.account_type = account_type
        
        # Select Risk Setting
        if self.account_type == "FUTURES":
            self.risk_per_trade = RISK_FUTURES
        else:
            self.risk_per_trade = RISK_SPOT
            
        self.max_daily_dd = MAX_DAILY_LOSS
        self.daily_loss = 0.0

    def update_equity(self, current_balance):
        self.equity = current_balance
        self.daily_loss = self.start_equity - self.equity

    def check_kill_switch(self):
        if self.start_equity <= 0: return False, ""
        drawdown_pct = self.daily_loss / self.start_equity
        if drawdown_pct >= self.max_daily_dd:
            return True, f"{self.account_type} Kill Switch: {drawdown_pct*100:.2f}% Hit"
        return False, ""

    def calculate_position_size(self, symbol, entry_price, stop_loss_price):
        if entry_price <= 0 or stop_loss_price <= 0: return 0.0
        
        # 1. Base Risk Sizing
        risk_amt = self.equity * self.risk_per_trade
        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0: return 0.0
        
        qty = risk_amt / price_diff
        
        if self.account_type == "FUTURES":
            # 2. Leverage & Liquidation Check (Futures Only)
            max_lev = LEVERAGE_MAP.get(symbol, 2)
            position_value = qty * entry_price
            max_allowed_value = self.equity * max_lev
            
            if position_value > max_allowed_value:
                qty = max_allowed_value / entry_price

            liq_dist = entry_price / max_lev 
            sl_dist = price_diff
            if liq_dist < (2 * sl_dist):
                print(f"⚠️ {self.account_type} Reject: Liq Risk too high.")
                return 0.0

        return qty
