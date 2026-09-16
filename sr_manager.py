"""
Support/Resistance Level Manager
Allows you to input key price levels via web terminal
Bot uses these to catch reversal signals + lower threshold
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class SRLevel:
    """Single S/R level with expiration"""
    def __init__(self, price: float, level_type: str, ttl_minutes: int = 240):
        self.price = price
        self.level_type = level_type  # "SUPPORT" or "RESISTANCE"
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
        self.hits = 0  # How many times price touched this level
    
    def is_expired(self) -> bool:
        """Check if level has expired"""
        return datetime.utcnow() > self.expires_at
    
    def time_remaining_minutes(self) -> float:
        """Minutes until expiration"""
        delta = (self.expires_at - datetime.utcnow()).total_seconds() / 60
        return max(0, delta)
    
    def to_dict(self):
        """Serialize to dict"""
        return {
            "price": self.price,
            "type": self.level_type,
            "created": self.created_at.isoformat(),
            "expires": self.expires_at.isoformat(),
            "time_remaining_min": round(self.time_remaining_minutes(), 1),
            "hits": self.hits
        }

class SRManager:
    """Manages support/resistance levels per symbol"""
    
    def __init__(self, persistence_file: str = "sr_levels.json"):
        self.levels = {}  # symbol -> [SRLevel, ...]
        self.persistence_file = persistence_file
        self.load_from_disk()
    
    # ============ ADD/REMOVE LEVELS ============
    
    def add_level(self, symbol: str, price: float, level_type: str, ttl_minutes: int = 240):
        """Add a new S/R level"""
        if symbol not in self.levels:
            self.levels[symbol] = []
        
        # Check if level already exists (within 0.01)
        for level in self.levels[symbol]:
            if abs(level.price - price) < 0.01:
                logger.warning(f"{symbol}: Level {price} already exists")
                return False
        
        level = SRLevel(price, level_type, ttl_minutes)
        self.levels[symbol].append(level)
        self.save_to_disk()
        
        logger.info(f"✓ Added {level_type} {price} to {symbol} (expires in {ttl_minutes} min)")
        return True
    
    def remove_level(self, symbol: str, price: float) -> bool:
        """Remove a level by price"""
        if symbol not in self.levels:
            return False
        
        self.levels[symbol] = [
            lvl for lvl in self.levels[symbol]
            if abs(lvl.price - price) > 0.01
        ]
        self.save_to_disk()
        logger.info(f"✓ Removed level {price} from {symbol}")
        return True
    
    def clear_symbol(self, symbol: str):
        """Clear all levels for a symbol"""
        if symbol in self.levels:
            self.levels[symbol] = []
            self.save_to_disk()
            logger.info(f"✓ Cleared all levels for {symbol}")
    
    def cleanup_expired(self):
        """Remove all expired levels"""
        for symbol in self.levels:
            expired_count = len([l for l in self.levels[symbol] if l.is_expired()])
            self.levels[symbol] = [l for l in self.levels[symbol] if not l.is_expired()]
            if expired_count > 0:
                logger.info(f"{symbol}: Removed {expired_count} expired levels")
        
        self.save_to_disk()
    
    # ============ QUERY LEVELS ============
    
    def get_levels(self, symbol: str) -> List[SRLevel]:
        """Get all active levels for a symbol"""
        self.cleanup_expired()
        return self.levels.get(symbol, [])
    
    def find_nearest_level(self, symbol: str, price: float) -> Tuple[SRLevel, float, str] or None:
        """
        Find nearest S/R level to price
        Returns: (level, distance, direction) or None
        """
        levels = self.get_levels(symbol)
        if not levels:
            return None
        
        nearest = min(levels, key=lambda l: abs(l.price - price))
        distance = abs(nearest.price - price)
        
        if nearest.price > price:
            direction = "↑ Above"
        else:
            direction = "↓ Below"
        
        return nearest, distance, direction
    
    def is_near_level(self, symbol: str, price: float, tolerance: float = 0.50) -> Tuple[bool, SRLevel, float] or Tuple[False, None, None]:
        """
        Check if price is near any S/R level (within tolerance)
        tolerance: how far price can be from level (default 0.50)
        """
        level, distance, direction = self.find_nearest_level(symbol, price) or (None, None, None)
        
        if level and distance <= tolerance:
            return True, level, distance
        
        return False, None, None
    
    # ============ REVERSAL BONUS LOGIC ============
    
    def get_reversal_bonus(self, symbol: str, price: float, rsi: float = None) -> Tuple[bool, float, str]:
        """
        Calculate if reversal bonus applies
        Returns: (applies, bonus_pct, reason)
        
        Logic:
        - Price within 0.50 of S/R level = 10% bonus
        - + RSI extreme (< 30 or > 70) = +5% bonus
        - Max bonus: 15%
        """
        is_near, level, distance = self.is_near_level(symbol, price, tolerance=0.50)
        
        if not is_near:
            return False, 0, ""
        
        bonus = 10.0  # Base: price near level
        reason = f"Near {level.level_type.lower()} {level.price:.2f} (${distance:.2f} away)"
        
        # Extra bonus if RSI is extreme
        if rsi is not None:
            if rsi < 30 or rsi > 70:
                bonus += 5.0
                reason += " + Extreme RSI"
        
        return True, min(bonus, 15.0), reason
    
    # ============ PERSISTENCE ============
    
    def save_to_disk(self):
        """Persist levels to JSON file"""
        try:
            data = {}
            for symbol, levels in self.levels.items():
                data[symbol] = [lvl.to_dict() for lvl in levels]
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving S/R levels: {e}")
    
    def load_from_disk(self):
        """Load levels from JSON file"""
        try:
            if not os.path.exists(self.persistence_file):
                return
            
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            self.levels = {}
            for symbol, level_dicts in data.items():
                self.levels[symbol] = []
                for ld in level_dicts:
                    # Recreate SRLevel from dict
                    level = SRLevel.__new__(SRLevel)
                    level.price = ld["price"]
                    level.level_type = ld["type"]
                    level.created_at = datetime.fromisoformat(ld["created"])
                    level.expires_at = datetime.fromisoformat(ld["expires"])
                    level.hits = ld.get("hits", 0)
                    
                    # Skip if expired
                    if not level.is_expired():
                        self.levels[symbol].append(level)
            
            logger.info(f"✓ Loaded S/R levels from disk")
        except Exception as e:
            logger.error(f"Error loading S/R levels: {e}")
    
    # ============ DISPLAY ============
    
    def display_levels(self, symbol: str):
        """Pretty-print levels for a symbol"""
        levels = self.get_levels(symbol)
        if not levels:
            return f"No active levels for {symbol}"
        
        msg = f"\n{'=' * 50}\n{symbol} S/R Levels\n{'=' * 50}\n"
        
        for lvl in sorted(levels, key=lambda x: x.price, reverse=True):
            time_left = lvl.time_remaining_minutes()
            msg += f"{lvl.level_type:12} ${lvl.price:8.2f} ({time_left:5.0f} min left)\n"
        
        return msg
