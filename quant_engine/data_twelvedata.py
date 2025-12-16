"""
Twelve Data API Adapter
=======================
Rate-limit-safe data provider for Forex, Stocks, and Crypto.
Designed for FREE PLAN: 8 credits/min, 800 credits/day.

Usage:
    adapter = TwelveDataAdapter(api_key)
    df = adapter.get_time_series("EUR/USD", interval="5min", outputsize=100)
    quote = adapter.get_quote("EUR/USD")
"""

import os
import time
import threading
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    """
    Token bucket rate limiter for Twelve Data API.
    FREE plan: 8 credits/min, 800 credits/day.
    """
    def __init__(self, per_minute=8, per_day=800):
        self.per_minute = per_minute
        self.per_day = per_day
        self.minute_window = deque()  # Timestamps of calls in last minute
        self.day_count = 0
        self.day_reset = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        self.lock = threading.Lock()
    
    def can_call(self, credits=1):
        """Check if we can make an API call."""
        with self.lock:
            now = datetime.now()
            
            # Reset daily counter at midnight
            if now >= self.day_reset:
                self.day_count = 0
                self.day_reset = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            
            # Clean old entries from minute window
            cutoff = time.time() - 60
            while self.minute_window and self.minute_window[0] < cutoff:
                self.minute_window.popleft()
            
            # Check limits
            if len(self.minute_window) + credits > self.per_minute:
                return False
            if self.day_count + credits > self.per_day:
                return False
            
            return True
    
    def record_call(self, credits=1):
        """Record that an API call was made."""
        with self.lock:
            self.minute_window.append(time.time())
            self.day_count += credits
    
    def get_status(self):
        """Get current rate limit status."""
        with self.lock:
            cutoff = time.time() - 60
            while self.minute_window and self.minute_window[0] < cutoff:
                self.minute_window.popleft()
            
            return {
                "minute_used": len(self.minute_window),
                "minute_limit": self.per_minute,
                "day_used": self.day_count,
                "day_limit": self.per_day,
                "minute_remaining": self.per_minute - len(self.minute_window),
                "day_remaining": self.per_day - self.day_count
            }


class DataCache:
    """
    TTL-based cache for API responses.
    TTL is aligned to timeframe (5min data = 5min cache).
    """
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
    
    def get(self, key):
        """Get cached data if not expired."""
        with self.lock:
            if key in self.cache:
                data, expires_at = self.cache[key]
                if time.time() < expires_at:
                    return data
                else:
                    del self.cache[key]
            return None
    
    def set(self, key, data, ttl_seconds):
        """Cache data with TTL."""
        with self.lock:
            self.cache[key] = (data, time.time() + ttl_seconds)
    
    def clear(self):
        """Clear all cached data."""
        with self.lock:
            self.cache.clear()


class TwelveDataAdapter:
    """
    Main adapter for Twelve Data API.
    Handles rate limiting, caching, and data formatting.
    """
    
    BASE_URL = "https://api.twelvedata.com"
    
    # Timeframe to seconds mapping for cache TTL
    INTERVAL_SECONDS = {
        "1min": 60,
        "5min": 300,
        "15min": 900,
        "30min": 1800,
        "1h": 3600,
        "4h": 14400,
        "1day": 86400
    }
    
    # Symbol mappings (Twelve Data format)
    FOREX_SYMBOLS = {
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "XAUUSD": "XAU/USD"  # Gold
    }
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("TWELVE_DATA_API_KEY")
        if not self.api_key:
            print("⚠️ TWELVE_DATA_API_KEY not set. Using demo mode.")
            self.api_key = "demo"
        
        self.rate_limiter = RateLimiter()
        self.cache = DataCache()
        self.last_error = None
        self.is_degraded = False
    
    def _make_request(self, endpoint, params, credits=1):
        """
        Make a rate-limited API request.
        Returns parsed JSON or None on error.
        """
        # Check rate limits
        if not self.rate_limiter.can_call(credits):
            self.last_error = "Rate limit exceeded"
            self.is_degraded = True
            print(f"⚠️ Twelve Data: Rate limit exceeded. Status: {self.rate_limiter.get_status()}")
            return None
        
        # Make request
        url = f"{self.BASE_URL}/{endpoint}"
        params["apikey"] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=10)
            self.rate_limiter.record_call(credits)
            
            if response.status_code == 429:
                self.last_error = "429 Too Many Requests"
                self.is_degraded = True
                print("⚠️ Twelve Data: 429 Too Many Requests")
                return None
            
            if response.status_code != 200:
                self.last_error = f"HTTP {response.status_code}"
                self.is_degraded = True
                return None
            
            data = response.json()
            
            # Check for API errors
            if "code" in data and data["code"] != 200:
                self.last_error = data.get("message", "Unknown API error")
                self.is_degraded = True
                print(f"⚠️ Twelve Data API Error: {self.last_error}")
                return None
            
            self.is_degraded = False
            self.last_error = None
            return data
            
        except requests.exceptions.Timeout:
            self.last_error = "Request timeout"
            self.is_degraded = True
            return None
        except Exception as e:
            self.last_error = str(e)
            self.is_degraded = True
            return None
    
    def get_quote(self, symbol):
        """
        Get latest price quote for a symbol.
        Returns dict with price, change, etc.
        """
        # Map symbol if needed
        td_symbol = self.FOREX_SYMBOLS.get(symbol.upper().replace("/", ""), symbol)
        
        # Check cache (30s TTL for quotes)
        cache_key = f"quote:{td_symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Make request
        data = self._make_request("quote", {"symbol": td_symbol})
        if not data:
            return None
        
        result = {
            "symbol": symbol,
            "price": float(data.get("close", 0)),
            "open": float(data.get("open", 0)),
            "high": float(data.get("high", 0)),
            "low": float(data.get("low", 0)),
            "change": float(data.get("change", 0)),
            "percent_change": float(data.get("percent_change", 0)),
            "timestamp": data.get("datetime", ""),
            "data_source": "TWELVE_DATA"
        }
        
        self.cache.set(cache_key, result, 30)  # 30s cache
        return result
    
    def get_time_series(self, symbol, interval="5min", outputsize=100):
        """
        Get historical candle data.
        Returns pandas DataFrame with OHLCV data.
        """
        # Map symbol
        td_symbol = self.FOREX_SYMBOLS.get(symbol.upper().replace("/", ""), symbol)
        
        # Calculate cache TTL based on interval
        ttl = self.INTERVAL_SECONDS.get(interval, 300)
        
        # Check cache
        cache_key = f"series:{td_symbol}:{interval}:{outputsize}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Make request
        data = self._make_request("time_series", {
            "symbol": td_symbol,
            "interval": interval,
            "outputsize": outputsize
        })
        
        if not data or "values" not in data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data["values"])
        
        # Format columns
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")
        
        # Build dtype mapping only for columns that exist
        dtype_map = {
            "open": float,
            "high": float,
            "low": float,
            "close": float
        }
        if "volume" in df.columns:
            dtype_map["volume"] = float
        
        df = df.astype(dtype_map)
        
        # Add synthetic volume for Forex (strategy expects it)
        if "volume" not in df.columns:
            df["volume"] = 1.0
        
        # Sort ascending (oldest first)
        df = df.sort_index()
        
        # Add metadata
        df.attrs["symbol"] = symbol
        df.attrs["interval"] = interval
        df.attrs["data_source"] = "TWELVE_DATA"
        
        self.cache.set(cache_key, df, ttl)
        return df
    
    def get_status(self):
        """Get adapter health status."""
        rate_status = self.rate_limiter.get_status()
        return {
            "healthy": not self.is_degraded,
            "degraded": self.is_degraded,
            "last_error": self.last_error,
            "rate_limits": rate_status,
            "data_source": "TWELVE_DATA"
        }


# Singleton instance
_adapter = None

def get_adapter():
    """Get or create the singleton adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = TwelveDataAdapter()
    return _adapter


if __name__ == "__main__":
    # Test the adapter
    adapter = TwelveDataAdapter()
    
    print("Testing Twelve Data Adapter...")
    print(f"Status: {adapter.get_status()}")
    
    # Test quote
    quote = adapter.get_quote("EUR/USD")
    print(f"EUR/USD Quote: {quote}")
    
    # Test time series
    df = adapter.get_time_series("EUR/USD", interval="5min", outputsize=10)
    print(f"EUR/USD 5min Data:\n{df}")
