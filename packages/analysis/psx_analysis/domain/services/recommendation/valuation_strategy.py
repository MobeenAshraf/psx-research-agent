from typing import Dict, Any, Tuple
from .recommendation_strategy import RecommendationStrategy


class ValuationStrategy(RecommendationStrategy):
    def evaluate(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[str, float, str]:
        pb = metrics.get('price_to_book')
        if not pb:
            return 'Hold', 0.4, "No P/B data"
        
        if pb < 1.0:
            return 'Buy', 0.65, f"Undervalued (P/B: {pb:.2f})"
        elif pb > 3.0:
            return 'Sell', 0.65, f"Overvalued (P/B: {pb:.2f})"
        return 'Hold', 0.5, f"Fair value (P/B: {pb:.2f})"

