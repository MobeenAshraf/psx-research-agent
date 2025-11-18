import pandas as pd
from typing import Dict, Optional


class IchimokuCalculator:
    """Calculate Ichimoku Cloud components."""
    
    def calculate(
        self, 
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Ichimoku Cloud components.
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            
        Returns:
            Dictionary with tenkan, kijun, senkou_a, senkou_b, chikou values
        """
        if high.empty or low.empty or close.empty or len(close) < 52:
            return {
                'tenkan': None,
                'kijun': None,
                'senkou_a': None,
                'senkou_b': None,
                'chikou': None
            }
        
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan_high = high.rolling(window=9).max()
        tenkan_low = low.rolling(window=9).min()
        tenkan = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        kijun_high = high.rolling(window=26).max()
        kijun_low = low.rolling(window=26).min()
        kijun = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted 26 periods forward
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods forward
        senkou_b_high = high.rolling(window=52).max()
        senkou_b_low = low.rolling(window=52).min()
        senkou_b = ((senkou_b_high + senkou_b_low) / 2).shift(26)
        
        # Chikou Span (Lagging Span): Close price shifted 26 periods backward
        chikou = close.shift(-26)
        
        return {
            'tenkan': float(tenkan.iloc[-1]) if not tenkan.empty and not pd.isna(tenkan.iloc[-1]) else None,
            'kijun': float(kijun.iloc[-1]) if not kijun.empty and not pd.isna(kijun.iloc[-1]) else None,
            'senkou_a': float(senkou_a.iloc[-1]) if not senkou_a.empty and not pd.isna(senkou_a.iloc[-1]) else None,
            'senkou_b': float(senkou_b.iloc[-1]) if not senkou_b.empty and not pd.isna(senkou_b.iloc[-1]) else None,
            'chikou': float(chikou.iloc[-1]) if not chikou.empty and not pd.isna(chikou.iloc[-1]) else None
        }

