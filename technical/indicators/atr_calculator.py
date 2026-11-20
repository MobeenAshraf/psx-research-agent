import pandas as pd
from typing import Optional

from technical.indicators.wilder import wilder_average


class ATRCalculator:
    """Calculate Average True Range (ATR) - volatility indicator."""
    
    def calculate(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            period: Period for ATR calculation (default: 14)
            
        Returns:
            Latest ATR value or None if insufficient data
        """
        if high.empty or low.empty or close.empty or len(close) < period + 1:
            return None
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return wilder_average(true_range.iloc[1:], period)
