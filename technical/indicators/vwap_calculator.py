import pandas as pd
from typing import Optional


class VWAPCalculator:
    """Calculate Volume Weighted Average Price (VWAP)."""
    
    def calculate(
        self, 
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series, 
        volumes: pd.Series
    ) -> Optional[float]:
        """
        Calculate Volume Weighted Average Price.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            volumes: Series of volumes
            
        Returns:
            Latest VWAP value or None if insufficient data
        """
        if high.empty or low.empty or close.empty or volumes.empty:
            return None
        
        if len(high) != len(low) != len(close) != len(volumes):
            return None
        
        # Calculate typical price (HLC/3)
        typical_price = (high + low + close) / 3
        
        # Calculate cumulative price * volume and cumulative volume
        cumulative_pv = (typical_price * volumes).cumsum()
        cumulative_volume = volumes.cumsum()
        
        # Calculate VWAP
        vwap = cumulative_pv / cumulative_volume
        
        return float(vwap.iloc[-1]) if not vwap.empty and not pd.isna(vwap.iloc[-1]) else None

