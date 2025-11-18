from typing import Dict, Any, Tuple
from technical.recommendation.recommendation_strategy import RecommendationStrategy


class RSIStrategy(RecommendationStrategy):
    def evaluate(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[str, float, str]:
        rsi = indicators.get('rsi')
        if rsi is None:
            return 'Hold', 0.4, "No RSI data"
        
        if rsi < 30:
            return 'Buy', 0.6, "RSI oversold"
        elif rsi > 70:
            return 'Sell', 0.6, "RSI overbought"
        return 'Hold', 0.5, "RSI neutral"

