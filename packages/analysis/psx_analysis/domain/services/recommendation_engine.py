from typing import Dict, Any, Tuple, List
from .recommendation import RSIStrategy, MACDStrategy, ValuationStrategy
from .confidence_calculator import ConfidenceCalculator


class RecommendationEngine:
    def __init__(self):
        self.strategies = [
            RSIStrategy(),
            MACDStrategy(),
            ValuationStrategy(),
        ]
        self.confidence_calculator = ConfidenceCalculator()
    
    def generate_recommendation(
        self,
        indicators: Dict[str, Any],
        metrics: Dict[str, Any],
        signals: List[str]
    ) -> Tuple[str, float, List[str]]:
        recommendation = 'Hold'
        reasoning = []
        strategy_results = []
        
        # Evaluate all strategies and collect results
        for strategy in self.strategies:
            rec, conf, reason = strategy.evaluate(indicators, metrics)
            strategy_results.append((rec, conf, reason))
            
            # Update recommendation based on strategy results
            if self._should_update_recommendation(rec, recommendation, conf):
                recommendation = rec
            reasoning.append(reason)
        
        # Calculate confidence based on data availability, signal strength, and agreement
        confidence = self.confidence_calculator.calculate_confidence(
            strategy_results, indicators, metrics, recommendation
        )
        
        reasoning.extend(signals)
        return recommendation, confidence, reasoning
    
    def _should_update_recommendation(
        self, new_rec: str, current_rec: str, new_conf: float
    ) -> bool:
        """
        Determine if recommendation should be updated.
        
        Priority:
        1. Buy/Sell signals override Hold
        2. Higher confidence signals override lower confidence
        3. Buy/Sell with confidence >= 0.5 override Hold
        """
        if current_rec == 'Hold' and new_rec != 'Hold':
            # Only update if new signal has reasonable confidence
            if new_conf >= 0.5:
                return True
        elif current_rec != 'Hold' and new_rec != 'Hold':
            # If both are Buy/Sell, prefer higher confidence
            if new_conf > 0.5:  # Only consider strong signals
                return True
        return False
