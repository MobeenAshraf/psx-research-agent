import pandas as pd
from typing import Dict, List


class TrendAnalyzer:
    def analyze_trend(self, prices: pd.Series, sma_20: float, sma_50: float) -> Dict:
        if prices.empty:
            return {}
        
        current_price = float(prices.iloc[-1])
        
        trend = 'Neutral'
        strength = 0.0
        
        if sma_20 and sma_50:
            if current_price > sma_20 > sma_50:
                trend = 'Uptrend'
                strength = 0.7
            elif current_price < sma_20 < sma_50:
                trend = 'Downtrend'
                strength = 0.7
            elif current_price > sma_20:
                trend = 'Bullish'
                strength = 0.5
            elif current_price < sma_20:
                trend = 'Bearish'
                strength = 0.5
        
        price_vs_sma20 = None
        price_vs_sma50 = None
        if sma_20:
            price_vs_sma20 = ((current_price - sma_20) / sma_20) * 100
        if sma_50:
            price_vs_sma50 = ((current_price - sma_50) / sma_50) * 100
        
        return {
            'trend': trend,
            'trend_strength': strength,
            'price_vs_sma20_pct': price_vs_sma20,
            'price_vs_sma50_pct': price_vs_sma50,
        }

