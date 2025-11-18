"""Confidence calculator for stock analysis recommendations."""

from typing import Dict, Any, List, Tuple
from collections import Counter


class ConfidenceCalculator:
    """Calculate confidence scores based on data availability, signal strength, and strategy agreement."""
    
    # Weights for different factors
    DATA_AVAILABILITY_WEIGHT = 0.3
    SIGNAL_STRENGTH_WEIGHT = 0.4
    STRATEGY_AGREEMENT_WEIGHT = 0.3
    
    def calculate_confidence(
        self,
        strategy_results: List[Tuple[str, float, str]],
        indicators: Dict[str, Any],
        metrics: Dict[str, Any],
        final_recommendation: str
    ) -> float:
        """
        Calculate confidence score based on multiple factors.
        
        Args:
            strategy_results: List of (recommendation, confidence, reason) tuples from each strategy
            indicators: Technical indicators dictionary
            metrics: Financial metrics dictionary
            final_recommendation: Final recommendation after combining strategies
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Factor 1: Data Availability (0.0 - 1.0)
        data_availability_score = self._calculate_data_availability(indicators, metrics)
        
        # Factor 2: Signal Strength (0.0 - 1.0)
        signal_strength_score = self._calculate_signal_strength(indicators, metrics, strategy_results)
        
        # Factor 3: Strategy Agreement (0.0 - 1.0)
        agreement_score = self._calculate_strategy_agreement(strategy_results, final_recommendation)
        
        # Weighted combination
        confidence = (
            data_availability_score * self.DATA_AVAILABILITY_WEIGHT +
            signal_strength_score * self.SIGNAL_STRENGTH_WEIGHT +
            agreement_score * self.STRATEGY_AGREEMENT_WEIGHT
        )
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _calculate_data_availability(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """
        Calculate score based on how many indicators/metrics are available.
        
        Returns:
            Score between 0.0 (no data) and 1.0 (all data available)
        """
        # Expected indicators
        expected_indicators = ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_50', 'current_price']
        # Expected metrics
        expected_metrics = ['price_to_book', 'book_value']
        
        available_indicators = sum(1 for key in expected_indicators if indicators.get(key) is not None)
        available_metrics = sum(1 for key in expected_metrics if metrics.get(key) is not None)
        
        indicator_score = available_indicators / len(expected_indicators) if expected_indicators else 0.0
        metric_score = available_metrics / len(expected_metrics) if expected_metrics else 0.0
        
        # Weight indicators more heavily (70%) than metrics (30%)
        return (indicator_score * 0.7 + metric_score * 0.3)
    
    def _calculate_signal_strength(self, indicators: Dict[str, Any], metrics: Dict[str, Any], 
                                   strategy_results: List[Tuple[str, float, str]]) -> float:
        """
        Calculate score based on how strong/extreme the signals are.
        
        Returns:
            Score between 0.0 (weak signals) and 1.0 (very strong signals)
        """
        if not strategy_results:
            return 0.0
        
        # Get average confidence from strategies (excluding missing data cases)
        valid_confidences = [conf for rec, conf, reason in strategy_results if conf >= 0.5]
        missing_data_count = sum(1 for rec, conf, reason in strategy_results if conf < 0.5)
        
        # Heavy penalty if most strategies have missing data
        if missing_data_count >= len(strategy_results) * 0.67:  # 2/3 or more missing
            return 0.2
        
        if not valid_confidences:
            return 0.2  # Low score if all strategies have missing data
        
        avg_confidence = sum(valid_confidences) / len(valid_confidences)
        
        # Penalize if average confidence is low (weak signals)
        if avg_confidence < 0.55:
            avg_confidence *= 0.8  # Reduce by 20%
        
        # Boost score for extreme RSI values
        rsi = indicators.get('rsi')
        rsi_boost = 0.0
        if rsi is not None:
            if rsi < 25 or rsi > 75:  # Very extreme
                rsi_boost = 0.2
            elif rsi < 30 or rsi > 70:  # Extreme
                rsi_boost = 0.1
        
        # Boost score for extreme P/B ratios
        pb = metrics.get('price_to_book')
        pb_boost = 0.0
        if pb is not None:
            if pb < 0.5 or pb > 5.0:  # Very extreme
                pb_boost = 0.2
            elif pb < 1.0 or pb > 3.0:  # Extreme
                pb_boost = 0.1
        
        # Combine base confidence with signal strength boosts
        signal_strength = avg_confidence + min(0.3, rsi_boost + pb_boost)
        
        return min(1.0, signal_strength)
    
    def _calculate_strategy_agreement(self, strategy_results: List[Tuple[str, float, str]], 
                                     final_recommendation: str) -> float:
        """
        Calculate score based on how much strategies agree with each other.
        
        Returns:
            Score between 0.0 (no agreement) and 1.0 (perfect agreement)
        """
        if not strategy_results:
            return 0.0
        
        # Count recommendations (excluding missing data cases)
        valid_recommendations = [rec for rec, conf, reason in strategy_results if conf >= 0.5]
        missing_data_count = sum(1 for rec, conf, reason in strategy_results if conf < 0.5)
        
        # Heavy penalty if most strategies have missing data
        if missing_data_count >= len(strategy_results) * 0.67:  # 2/3 or more missing
            return 0.2
        
        if not valid_recommendations:
            return 0.2  # Low agreement if all strategies have missing data
        
        # Count how many strategies agree with final recommendation
        agreement_count = sum(1 for rec in valid_recommendations if rec == final_recommendation)
        total_count = len(valid_recommendations)
        
        # Base agreement score
        agreement_ratio = agreement_count / total_count if total_count > 0 else 0.0
        
        # If final recommendation is Hold and all valid strategies also say Hold, that's agreement
        # But if we have very few valid strategies, reduce agreement score
        if total_count < len(strategy_results) * 0.5:  # Less than half have valid data
            agreement_ratio *= 0.7
        
        # Boost if all strategies agree
        if agreement_count == total_count and total_count >= 2:
            agreement_ratio = min(1.0, agreement_ratio + 0.2)
        
        # Penalize if strategies strongly disagree (e.g., some say Buy, some say Sell)
        rec_counts = Counter(valid_recommendations)
        if len(rec_counts) > 1:
            # If we have both Buy and Sell signals, heavily reduce agreement
            if 'Buy' in rec_counts and 'Sell' in rec_counts:
                agreement_ratio *= 0.5  # Strong penalty for conflicting signals
            # Also penalize if we have mixed Buy/Hold or Sell/Hold with significant disagreement
            elif agreement_ratio < 0.67:  # Less than 2/3 agreement
                agreement_ratio *= 0.8
        
        return agreement_ratio

