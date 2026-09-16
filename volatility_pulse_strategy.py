import numpy as np
import logging

logger = logging.getLogger(__name__)

class VolatilityPulseStrategy:
    """
    Volatility Pulse Strategy for Deriv Indices
    
    Scoring system:
    - 1H: 0-5 pts (trend direction + strength)
    - 15M: 0-9 pts (pullback exhaustion + SAR flip bonus)
    - 5M: 0-6 pts (reversal entry + candle quality)
    - Total: max 20 pts (signal fires at ≥10)
    """
    
    # ATR and SAR multipliers per index
    MULTIPLIERS = {
        "R_10": {"sl": 1.2, "tp": 2.4, "sar_af": 0.02, "sar_max": 0.2},
        "R_25": {"sl": 1.3, "tp": 2.6, "sar_af": 0.02, "sar_max": 0.2},
        "R_50": {"sl": 1.5, "tp": 3.0, "sar_af": 0.02, "sar_max": 0.25},
        "R_75": {"sl": 2.0, "tp": 4.0, "sar_af": 0.03, "sar_max": 0.3}
    }
    
    def __init__(self):
        pass
    
    # ============ INDICATORS ============
    
    def ema(self, candles, period):
        """Exponential Moving Average"""
        closes = np.array([c["close"] for c in candles])
        if len(closes) < period:
            return None
        
        ema = np.zeros(len(closes))
        ema[0] = closes[0]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(closes)):
            ema[i] = closes[i] * multiplier + ema[i-1] * (1 - multiplier)
        
        return ema[-1]
    
    def rsi(self, candles, period=14):
        """Relative Strength Index"""
        closes = np.array([c["close"] for c in candles])
        if len(closes) < period:
            return None
        
        deltas = np.diff(closes)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        
        rsi = 100 - 100 / (1 + rs)
        
        for d in deltas[period+1:]:
            up = (up * (period - 1) + (d if d > 0 else 0)) / period
            down = (down * (period - 1) + (-d if d < 0 else 0)) / period
            rs = up / down if down != 0 else 0
            rsi = 100 - 100 / (1 + rs)
        
        return rsi
    
    def macd(self, candles):
        """MACD (12, 26, 9)"""
        closes = np.array([c["close"] for c in candles])
        if len(closes) < 26:
            return None, None, None
        
        ema12 = self._ema_array(closes, 12)
        ema26 = self._ema_array(closes, 26)
        
        macd_line = ema12 - ema26
        signal_line = self._ema_array(macd_line, 9)
        histogram = macd_line - signal_line
        
        return macd_line[-1], signal_line[-1], histogram[-1]
    
    def atr(self, candles, period=14):
        """Average True Range"""
        if len(candles) < period:
            return None
        
        trs = []
        for i in range(len(candles)):
            if i == 0:
                tr = candles[i]["high"] - candles[i]["low"]
            else:
                h = candles[i]["high"]
                l = candles[i]["low"]
                c = candles[i-1]["close"]
                tr = max(h - l, abs(h - c), abs(l - c))
            trs.append(tr)
        
        atr = np.mean(trs[-period:])
        return atr
    
    def adx(self, candles, period=14):
        """Average Directional Index"""
        if len(candles) < period:
            return None
        
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        
        # Calculate +DM and -DM
        plus_dm = np.zeros(len(candles))
        minus_dm = np.zeros(len(candles))
        
        for i in range(1, len(candles)):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            
            if up > down and up > 0:
                plus_dm[i] = up
            if down > up and down > 0:
                minus_dm[i] = down
        
        # Calculate TR and ATR
        trs = []
        for i in range(len(candles)):
            if i == 0:
                tr = candles[i]["high"] - candles[i]["low"]
            else:
                tr = max(
                    candles[i]["high"] - candles[i]["low"],
                    abs(candles[i]["high"] - candles[i-1]["close"]),
                    abs(candles[i]["low"] - candles[i-1]["close"])
                )
            trs.append(tr)
        
        atr = np.mean(trs[-period:])
        
        # Calculate +DI and -DI
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr if atr > 0 else 0
        
        # Calculate ADX
        di_diff = abs(plus_di - minus_di)
        di_sum = plus_di + minus_di
        dx = 100 * di_diff / di_sum if di_sum > 0 else 0
        adx = dx  # Simplified; real ADX smooths DX over period
        
        return adx
    
    def parabolic_sar(self, candles, symbol="R_10"):
        """Parabolic SAR with index-specific AF"""
        config = self.MULTIPLIERS[symbol]
        af = config["sar_af"]
        max_af = config["sar_max"]
        
        if len(candles) < 5:
            return None, None
        
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        
        # Simplified SAR calculation
        sar = candles[0]["low"]
        ep = candles[0]["high"]
        uptrend = True
        
        for i in range(1, len(candles)):
            if uptrend:
                sar = sar + af * (ep - sar)
                sar = min(sar, lows[i-1], lows[i])
                
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + 0.02, max_af)
                
                if lows[i] < sar:
                    uptrend = False
                    sar = ep
                    ep = lows[i]
                    af = config["sar_af"]
            else:
                sar = sar - af * (sar - ep)
                sar = max(sar, highs[i-1], highs[i])
                
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + 0.02, max_af)
                
                if highs[i] > sar:
                    uptrend = True
                    sar = ep
                    ep = highs[i]
                    af = config["sar_af"]
        
        return sar, uptrend
    
    # ============ STRATEGY SCORING ============
    
    def score_1h(self, candles_1h):
        """Score 1H macro bias (0-5 pts)"""
        if not candles_1h or len(candles_1h) < 50:
            return 0, "Insufficient 1H data"
        
        score = 0
        reasons = []
        
        ema20 = self.ema(candles_1h, 20)
        ema50 = self.ema(candles_1h, 50)
        ema200 = self.ema(candles_1h, 200)
        close = candles_1h[-1]["close"]
        
        if not all([ema20, ema50, ema200]):
            return 0, "EMAs not ready"
        
        # Trend direction (0-3 pts)
        if close > ema20 > ema50 > ema200:
            score += 3
            reasons.append("Strong uptrend (20>50>200)")
        elif close < ema20 < ema50 < ema200:
            score += 3
            reasons.append("Strong downtrend (20<50<200)")
        elif ema20 > ema50:
            score += 1
            reasons.append("Mild uptrend (20>50)")
        elif ema20 < ema50:
            score += 1
            reasons.append("Mild downtrend (20<50)")
        
        # Trend strength via ADX (0-2 pts)
        adx = self.adx(candles_1h)
        if adx and adx >= 20:
            score += 2
            reasons.append(f"Strong trend (ADX {adx:.1f})")
        elif adx and adx >= 15:
            score += 1
            reasons.append(f"Moderate trend (ADX {adx:.1f})")
        
        return score, " | ".join(reasons)
    
    def score_15m(self, candles_15m, symbol="R_10"):
        """Score 15M pullback exhaustion (0-9 pts)"""
        if not candles_15m or len(candles_15m) < 30:
            return 0, "Insufficient 15M data"
        
        score = 0
        reasons = []
        
        ema20 = self.ema(candles_15m, 20)
        rsi = self.rsi(candles_15m)
        sar, uptrend = self.parabolic_sar(candles_15m, symbol)
        
        if not ema20 or not rsi:
            return 0, "Indicators not ready"
        
        close = candles_15m[-1]["close"]
        
        # Pullback exhaustion (0-6 pts)
        if rsi < 30:
            score += 3
            reasons.append(f"Oversold RSI {rsi:.1f}")
        elif rsi < 35:
            score += 2
            reasons.append(f"Near oversold RSI {rsi:.1f}")
        elif rsi > 70:
            score += 3
            reasons.append(f"Overbought RSI {rsi:.1f}")
        elif rsi > 65:
            score += 2
            reasons.append(f"Near overbought RSI {rsi:.1f}")
        
        # 9 EMA retracement bonus (0-3 pts)
        ema9 = self.ema(candles_15m, 9)
        if ema9:
            retrace_pct = abs(close - ema9) / ema9 * 100
            if retrace_pct < 0.5:
                score += 3
                reasons.append(f"9 EMA kiss (retrace {retrace_pct:.2f}%)")
            elif retrace_pct < 1.0:
                score += 2
                reasons.append(f"Close to 9 EMA (retrace {retrace_pct:.2f}%)")
            elif retrace_pct < 1.5:
                score += 1
                reasons.append(f"9 EMA nearby (retrace {retrace_pct:.2f}%)")
        
        # SAR flip bonus (0-2 pts)
        if sar:
            if (uptrend and close > sar) or (not uptrend and close < sar):
                score += 2
                reasons.append("SAR flip reversal signal")
        
        return min(score, 9), " | ".join(reasons)
    
    def score_5m(self, candles_5m, symbol="R_10"):
        """Score 5M reversal entry (0-6 pts)"""
        if not candles_5m or len(candles_5m) < 20:
            return 0, "Insufficient 5M data"
        
        score = 0
        reasons = []
        
        rsi = self.rsi(candles_5m)
        macd_val, signal, histogram = self.macd(candles_5m)
        
        if not rsi:
            return 0, "5M RSI not ready"
        
        # Entry trigger via RSI (0-3 pts)
        if rsi < 25 or rsi > 75:
            score += 3
            reasons.append(f"Extreme RSI {rsi:.1f}")
        elif rsi < 30 or rsi > 70:
            score += 2
            reasons.append(f"Oversold/overbought RSI {rsi:.1f}")
        elif rsi < 35 or rsi > 65:
            score += 1
            reasons.append(f"Near extreme RSI {rsi:.1f}")
        
        # MACD confirmation (0-2 pts)
        if macd_val is not None and signal is not None:
            if (macd_val > signal and histogram > 0):
                score += 2
                reasons.append("MACD bullish crossover")
            elif (macd_val < signal and histogram < 0):
                score += 2
                reasons.append("MACD bearish crossover")
            elif (macd_val > signal or histogram > 0):
                score += 1
                reasons.append("MACD bullish signal")
            elif (macd_val < signal or histogram < 0):
                score += 1
                reasons.append("MACD bearish signal")
        
        # Candle quality (0-1 pt)
        if len(candles_5m) >= 2:
            prev_close = candles_5m[-2]["close"]
            curr_close = candles_5m[-1]["close"]
            curr_open = candles_5m[-1]["open"]
            
            candle_range = candles_5m[-1]["high"] - candles_5m[-1]["low"]
            body_range = abs(curr_close - curr_open)
            
            if body_range > candle_range * 0.6:  # Strong candle
                score += 1
                reasons.append("Strong candle body")
        
        return min(score, 6), " | ".join(reasons)
    
    def analyze(self, symbol, candles_1h, candles_15m, candles_5m):
        """
        Full analysis with combined scoring
        Returns: (total_score, max_score, direction, details_dict)
        """
        score_1h, reasons_1h = self.score_1h(candles_1h)
        score_15m, reasons_15m = self.score_15m(candles_15m, symbol)
        score_5m, reasons_5m = self.score_5m(candles_5m, symbol)
        
        total_score = score_1h + score_15m + score_5m
        max_score = 20
        
        # Determine direction from 1H bias
        if candles_1h and len(candles_1h) >= 20:
            ema20 = self.ema(candles_1h, 20)
            ema50 = self.ema(candles_1h, 50)
            direction = "UP" if (ema20 and ema50 and ema20 > ema50) else "DOWN"
        else:
            direction = "NEUTRAL"
        
        # Calculate confluence percentage
        confluence_pct = (total_score / max_score) * 100
        
        details = {
            "total_score": total_score,
            "max_score": max_score,
            "confluence_pct": confluence_pct,
            "direction": direction,
            "score_1h": score_1h,
            "score_15m": score_15m,
            "score_5m": score_5m,
            "reasons_1h": reasons_1h,
            "reasons_15m": reasons_15m,
            "reasons_5m": reasons_5m,
            "signal_fired": total_score >= 10 and score_1h >= 1 and score_15m >= 1 and score_5m >= 1
        }
        
        return total_score, max_score, direction, details
    
    # ============ HELPERS ============
    
    def _ema_array(self, data, period):
        """Helper: EMA for entire array"""
        ema = np.zeros(len(data))
        ema[0] = data[0]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(data)):
            ema[i] = data[i] * multiplier + ema[i-1] * (1 - multiplier)
        
        return ema
    
    def get_quality_label(self, confluence_pct):
        """Get quality emoji + label based on confluence %"""
        if confluence_pct >= 87:
            return "🔥 Exceptional"
        elif confluence_pct >= 73:
            return "💪 Very Strong"
        elif confluence_pct >= 67:
            return "✅ Strong"
        elif confluence_pct >= 60:
            return "👍 Good"
        elif confluence_pct >= 53:
            return "⚡ Valid"
        else:
            return "❌ Weak"
