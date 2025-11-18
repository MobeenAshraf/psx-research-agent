from typing import Dict, Any, Tuple
from technical.recommendation.recommendation_strategy import RecommendationStrategy


class MACDStrategy(RecommendationStrategy):
    def evaluate(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[str, float, str]:
        macd = indicators.get('macd')
        signal = indicators.get('macd_signal')
        if not macd or not signal:
            return 'Hold', 0.4, "No MACD data"
        
        if macd > signal:
            return 'Buy', 0.55, "Bullish MACD"
        return 'Sell', 0.55, "Bearish MACD"

