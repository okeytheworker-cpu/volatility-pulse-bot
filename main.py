#!/usr/bin/env python3
"""
Volatility Pulse Bot for Deriv Indices
Synthetic indices trading signals (R_10, R_25, R_50, R_75)
Delivery: WhatsApp via Green API
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

from deriv_websocket import DérivAPI
from volatility_pulse_strategy import VolatilityPulseStrategy
from whatsapp_sender import WhatsAppSender
from sr_manager import SRManager

# ============ SETUP ============

# Load environment
load_dotenv(".env")

DERIV_TOKEN = os.getenv("DERIV_API_TOKEN")
GREEN_INSTANCE = os.getenv("GREEN_API_INSTANCE_ID")
GREEN_TOKEN = os.getenv("GREEN_API_TOKEN")
WHATSAPP_GROUP = os.getenv("WHATSAPP_GROUP_ID")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", 300))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('volatility_pulse.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ BOT CLASS ============

class VolatilityPulseBot:
    def __init__(self):
        self.deriv = DérivAPI(DERIV_TOKEN)
        self.strategy = VolatilityPulseStrategy()
        self.whatsapp = WhatsAppSender(GREEN_INSTANCE, GREEN_TOKEN)
        self.sr_manager = SRManager("sr_levels.json")  # Load S/R levels
        
        # Indices to trade
        self.symbols = ["R_10", "R_25", "R_50", "R_75"]
        
        # Track last signal time per symbol (cooldown)
        self.last_signal_time = defaultdict(lambda: datetime.min)
        self.cooldown_minutes = 240  # 4-hour cooldown per index
        
        # Track signals sent (for logging)
        self.signals_log = []
        
        # Signal threshold (can be lowered by S/R bonus)
        self.base_threshold = 75.0  # 75%
        
        # For Replit: load signals from file instead of log
        self.signals_file = "signals_log.json"
        self._load_signals_log()
    
    def start(self):
        """Start the bot"""
        logger.info("=" * 60)
        logger.info("VOLATILITY PULSE BOT STARTING (Replit Edition)")
        logger.info("=" * 60)
        
        # Verify credentials
        if not self._verify_setup():
            logger.error("Setup verification failed. Exiting.")
            return False
        
        logger.info("Bot initialized. Starting scan loop...")
        logger.info(f"Scan interval: {SCAN_INTERVAL} seconds")
        logger.info(f"Monitoring: {', '.join(self.symbols)}")
        
        # Main loop
        try:
            self._scan_loop()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            logger.info("Bot shutdown complete")
    
    def _verify_setup(self):
        """Verify all credentials and connections"""
        logger.info("Verifying setup...")
        
        checks = {
            "Deriv API Token": DERIV_TOKEN,
            "Green API Instance": GREEN_INSTANCE,
            "Green API Token": GREEN_TOKEN,
            "WhatsApp Group ID": WHATSAPP_GROUP
        }
        
        for check, value in checks.items():
            if not value:
                logger.error(f"✗ Missing: {check}")
                return False
            logger.info(f"✓ {check} configured")
        
        # Test Green API
        if not self.whatsapp.get_account_status():
            logger.error("✗ Green API account inactive")
            return False
        
        logger.info("✓ Setup verification passed")
        return True
    
    def _scan_loop(self):
        """Main scanning loop - runs every SCAN_INTERVAL seconds"""
        while True:
            try:
                current_time = datetime.utcnow()
                logger.info(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}] Scanning indices...")
                
                # Fetch all candles from Deriv API
                all_candles = self.deriv.fetch_all_symbols()
                
                # Analyze each symbol
                for symbol in self.symbols:
                    if symbol in all_candles:
                        candles = all_candles[symbol]
                        self._analyze_symbol_with_candles(
                            symbol, 
                            candles.get("1h", []),
                            candles.get("15m", []),
                            candles.get("5m", []),
                            current_time
                        )
                
                # Wait before next scan
                logger.info(f"Waiting {SCAN_INTERVAL}s until next scan...")
                time.sleep(SCAN_INTERVAL)
                
            except Exception as e:
                logger.error(f"Scan loop error: {e}", exc_info=True)
                time.sleep(30)
    
    def _analyze_symbol_with_candles(self, symbol, candles_1h, candles_15m, candles_5m, current_time):
        """Analyze single symbol with pre-fetched candles"""
        try:
            
            if not candles_5m or not candles_15m or not candles_1h:
                logger.debug(f"{symbol}: Insufficient candle data")
                return
            
            # Run strategy
            score, max_score, direction, details = self.strategy.analyze(
                symbol, candles_1h, candles_15m, candles_5m
            )
            
            # Apply S/R bonus (if applicable)
            confluence_pct = details["confluence_pct"]
            current_price = candles_5m[-1]["close"]
            rsi = self.strategy.rsi(candles_5m)
            
            sr_applies, sr_bonus, sr_reason = self.sr_manager.get_reversal_bonus(
                symbol, current_price, rsi
            )
            
            effective_threshold = self.base_threshold
            if sr_applies:
                confluence_pct = min(confluence_pct + sr_bonus, 100)
                effective_threshold = max(60.0, self.base_threshold - sr_bonus)  # Lower threshold
                logger.info(f"{symbol}: S/R Bonus +{sr_bonus:.0f}% | {sr_reason}")
            
            # Log analysis (percentage-based)
            logger.info(
                f"{symbol}: {confluence_pct:.0f}% | Dir {direction} | "
                f"Threshold: {effective_threshold:.0f}%"
            )
            
            # Check if signal should fire
            if confluence_pct >= effective_threshold:
                # Check cooldown
                time_since_last = (current_time - self.last_signal_time[symbol]).total_seconds() / 60
                
                if time_since_last < self.cooldown_minutes:
                    logger.info(
                        f"{symbol}: Signal blocked (cooldown: {self.cooldown_minutes - time_since_last:.0f} "
                        f"min remaining)"
                    )
                    return
                
                # Signal confirmed - send to WhatsApp
                self._fire_signal(symbol, candles_1h, candles_5m, details, current_time)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
    
    def _fire_signal(self, symbol, candles_1h, candles_5m, details, current_time):
        """Fire signal and send to WhatsApp"""
        try:
            logger.info(f"🔥 SIGNAL FIRED: {symbol} {details['direction']}")
            
            # Calculate entry and targets
            current_price = candles_5m[-1]["close"]
            atr = self.strategy.atr(candles_5m)
            
            if not atr:
                logger.error(f"Cannot calculate ATR for {symbol}")
                return
            
            # Get multipliers for this index
            multipliers = self.strategy.MULTIPLIERS[symbol]
            sl_pct = multipliers["sl"]
            tp_pct = multipliers["tp"]
            
            # Calculate S/L and T/P
            if details["direction"] == "UP":
                sl = current_price - (atr * sl_pct)
                tp = current_price + (atr * tp_pct)
            else:
                sl = current_price + (atr * sl_pct)
                tp = current_price - (atr * tp_pct)
            
            # Entry zone (price ± ATR * 0.3)
            zone_size = atr * 0.3
            entry_zone = {
                "low": current_price - zone_size,
                "high": current_price + zone_size
            }
            
            # Calculate R:R
            risk = abs(current_price - sl)
            reward = abs(tp - current_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Prepare signal data
            signal_data = {
                "symbol": symbol,
                "direction": details["direction"],
                "entry_price": current_price,
                "entry_zone": entry_zone,
                "sl": sl,
                "tp": tp,
                "rr_ratio": rr_ratio,
                "confluence_pct": details["confluence_pct"],
                "quality_label": self.strategy.get_quality_label(details["confluence_pct"]),
                "total_score": details["total_score"],
                "score_1h": details["score_1h"],
                "score_15m": details["score_15m"],
                "score_5m": details["score_5m"]
            }
            
            # Send to WhatsApp
            success = self.whatsapp.send_signal(WHATSAPP_GROUP, signal_data)
            
            if success:
                self.last_signal_time[symbol] = current_time
                self.signals_log.append({
                    "timestamp": current_time.isoformat(),
                    "symbol": symbol,
                    "direction": details["direction"],
                    "confluence": details["confluence_pct"]
                })
                self._save_signals_log()  # Persist to disk
                logger.info(f"✓ {symbol} signal delivered to WhatsApp")
            else:
                logger.error(f"✗ Failed to send {symbol} signal")
        
        except Exception as e:
            logger.error(f"Error firing signal for {symbol}: {e}", exc_info=True)
    
    def _load_signals_log(self):
        """Load signals from file (Replit doesn't persist memory)"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r') as f:
                    data = json.load(f)
                    self.signals_log = data.get('signals', [])
                    logger.info(f"Loaded {len(self.signals_log)} previous signals from disk")
        except Exception as e:
            logger.error(f"Error loading signals log: {e}")
    
    def _save_signals_log(self):
        """Save signals to file (Replit persistence)"""
        try:
            with open(self.signals_file, 'w') as f:
                json.dump({'signals': self.signals_log}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving signals log: {e}")
    
    def print_stats(self):
        """Print bot statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("BOT STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Signals sent: {len(self.signals_log)}")
        
        if self.signals_log:
            for sig in self.signals_log[-10:]:  # Last 10 signals
                logger.info(
                    f"  {sig['timestamp']} | "
                    f"{sig['symbol']} {sig['direction']} | "
                    f"Conf {sig['confluence']:.0f}%"
                )

# ============ MAIN ============

if __name__ == "__main__":
    bot = VolatilityPulseBot()
    bot.start()
