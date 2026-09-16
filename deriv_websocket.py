import requests
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class DérivAPI:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://api.deriv.com/api/v3"
        self.candles = defaultdict(lambda: {"5m": [], "15m": [], "1h": []})
        self.last_fetch = defaultdict(lambda: datetime.min)
        
        # Volatility indices
        self.symbols = ["R_10", "R_25", "R_50", "R_75"]
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = 50) -> list:
        """
        Fetch candles from Deriv API
        timeframe: "5m", "15m", "1h"
        """
        try:
            # Map timeframe to seconds
            tf_map = {"5m": 300, "15m": 900, "1h": 3600}
            granularity = tf_map.get(timeframe, 300)
            
            payload = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": limit * 2,  # Get extra to build candles
                "end": "latest",
                "granularity": granularity,
                "style": "candles"
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"{symbol} {timeframe} fetch failed: {response.status_code}")
                return []
            
            data = response.json()
            
            if "candles" not in data:
                logger.debug(f"{symbol} {timeframe}: No candles in response")
                return []
            
            candles = []
            for candle in data["candles"]:
                candles.append({
                    "time": candle["epoch"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle.get("volume", 0)
                })
            
            return candles
        
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe}: {e}")
            return []
    
    def fetch_all_symbols(self) -> dict:
        """Fetch latest candles for all symbols"""
        result = {}
        for symbol in self.symbols:
            candles_5m = self.get_candles(symbol, "5m", limit=50)
            candles_15m = self.get_candles(symbol, "15m", limit=100)
            candles_1h = self.get_candles(symbol, "1h", limit=200)
            
            result[symbol] = {
                "5m": candles_5m,
                "15m": candles_15m,
                "1h": candles_1h
            }
            
            time.sleep(0.5)  # Rate limit
        
        return result

