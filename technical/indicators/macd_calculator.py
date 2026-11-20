from typing import Dict
import pandas as pd


class MACDCalculator:
    def calculate(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        crossover = None
        if len(macd) >= slow + signal:
            previous, current = (macd - signal_line).iloc[-2:]
            if previous <= 0 < current:
                crossover = "bullish"
            elif previous >= 0 > current:
                crossover = "bearish"
        return {
            'macd': float(macd.iloc[-1]) if not macd.empty else None,
            'crossover': crossover,
            'signal': float(signal_line.iloc[-1]) if not signal_line.empty else None,
        }

