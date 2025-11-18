import pandas as pd
from typing import Dict, Optional


class StochasticCalculator:
    """Calculate Stochastic Oscillator (%K and %D)."""
    
    def calculate(
        self, 
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series, 
        k_period: int = 14, 
        d_period: int = 3
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            k_period: Period for %K calculation (default: 14)
            d_period: Period for %D smoothing (default: 3)
            
        Returns:
            Dictionary with 'stoch_k' and 'stoch_d' values
        """
        if high.empty or low.empty or close.empty or len(close) < k_period:
            return {'stoch_k': None, 'stoch_d': None}
        
        # Calculate %K (Raw Stochastic)
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        # Calculate %K, handling division by zero (when high == low over period)
        denominator = highest_high - lowest_low
        numerator = close - lowest_low
        stoch_k = 100 * (numerator / denominator.replace(0, pd.NA))
        
        # Calculate %D (Smoothed %K)
        stoch_d = stoch_k.rolling(window=d_period).mean()
        
        return {
            'stoch_k': float(stoch_k.iloc[-1]) if not stoch_k.empty and not pd.isna(stoch_k.iloc[-1]) else None,
            'stoch_d': float(stoch_d.iloc[-1]) if not stoch_d.empty and not pd.isna(stoch_d.iloc[-1]) else None
        }

