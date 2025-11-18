import pandas as pd
from typing import Dict, Optional


class OBVCalculator:
    """Calculate On-Balance Volume (OBV) - volume-based trend indicator."""
    
    def calculate(self, prices: pd.Series, volumes: pd.Series) -> Dict[str, Optional[float]]:
        """
        Calculate On-Balance Volume and trend.
        
        Args:
            prices: Series of closing prices
            volumes: Series of volumes
            
        Returns:
            Dictionary with 'obv' (latest value) and 'obv_trend' (trend direction: 1=up, -1=down, 0=neutral)
        """
        if prices.empty or volumes.empty or len(prices) != len(volumes):
            return {'obv': None, 'obv_trend': None}
        
        # Calculate price change direction
        price_change = prices.diff()
        
        # Initialize OBV with first volume
        obv_values = [volumes.iloc[0]]
        
        # Calculate OBV: add volume if price up, subtract if price down, keep same if unchanged
        for i in range(1, len(prices)):
            prev_obv = obv_values[-1]
            if price_change.iloc[i] > 0:
                obv_values.append(prev_obv + volumes.iloc[i])
            elif price_change.iloc[i] < 0:
                obv_values.append(prev_obv - volumes.iloc[i])
            else:
                obv_values.append(prev_obv)
        
        obv = pd.Series(obv_values, index=prices.index)
        latest_obv = float(obv.iloc[-1]) if not obv.empty and not pd.isna(obv.iloc[-1]) else None
        
        # Determine trend by comparing recent OBV values (last 10 vs previous 10)
        trend = None
        if latest_obv is not None and len(obv) >= 20:
            recent_avg = obv.tail(10).mean()
            previous_avg = obv.iloc[-20:-10].mean()
            
            if recent_avg > previous_avg * 1.01:  # 1% threshold to avoid noise
                trend = 1  # Trending up
            elif recent_avg < previous_avg * 0.99:
                trend = -1  # Trending down
            else:
                trend = 0  # Neutral/flat
        
        return {
            'obv': latest_obv,
            'obv_trend': trend
        }

