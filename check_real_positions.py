import os
import time
from quant_engine.execution_futures import FuturesExecution

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

if not BINANCE_API_KEY:
    print("NO API KEY")
    exit()

exec = FuturesExecution(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
print("Querying Binance Futures Testnet Position Risk...")
positions = exec.get_positions()
print(f"Active Positions Found: {len(positions)}")
for p in positions:
    print(p)
