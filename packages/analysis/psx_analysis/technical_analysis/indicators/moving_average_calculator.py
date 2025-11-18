import pandas as pd
from typing import Dict


class MovingAverageCalculator:
    def calculate_sma(self, prices: pd.Series, period: int) -> float:
        sma = prices.rolling(period).mean()
        return float(sma.iloc[-1]) if not sma.empty else None
    
    def calculate_ema(self, prices: pd.Series, period: int) -> float:
        ema = prices.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1]) if not ema.empty else None

