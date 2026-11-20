from math import isclose, isfinite
from typing import Dict, Any, Tuple

from technical.recommendation.recommendation_strategy import RecommendationStrategy


class MACDStrategy(RecommendationStrategy):
    def evaluate(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[str, float, str]:
        macd = indicators.get("macd")
        signal = indicators.get("macd_signal")
        if macd is None or signal is None or not isfinite(macd) or not isfinite(signal):
            return "Hold", 0.0, "MACD data unavailable"
        if isclose(macd, signal, rel_tol=1e-9, abs_tol=1e-12):
            return "Hold", 0.0, "MACD and its signal line are level"
        if macd > signal:
            return "Buy", 0.55, "MACD above its signal line"
        return "Sell", 0.55, "MACD below its signal line"
