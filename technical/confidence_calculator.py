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
        """Calculate confidence score based on multiple factors."""
        data_availability_score = self._calculate_data_availability(indicators, metrics)
        signal_strength_score = self._calculate_signal_strength(indicators, metrics, strategy_results)
        agreement_score = self._calculate_strategy_agreement(strategy_results, final_recommendation)
        
        confidence = (
            data_availability_score * self.DATA_AVAILABILITY_WEIGHT +
            signal_strength_score * self.SIGNAL_STRENGTH_WEIGHT +
            agreement_score * self.STRATEGY_AGREEMENT_WEIGHT
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_data_availability(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """Score from 0.0-1.0 based on data availability."""
        expected_indicators = ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_50', 'current_price']
        expected_metrics = ['price_to_book', 'book_value']
        
        available_indicators = sum(1 for key in expected_indicators if indicators.get(key) is not None)
        available_metrics = sum(1 for key in expected_metrics if metrics.get(key) is not None)
        
        indicator_score = available_indicators / len(expected_indicators) if expected_indicators else 0.0
        metric_score = available_metrics / len(expected_metrics) if expected_metrics else 0.0
        
        return (indicator_score * 0.7 + metric_score * 0.3)
    
    def _calculate_signal_strength(self, indicators: Dict[str, Any], metrics: Dict[str, Any], 
                                   strategy_results: List[Tuple[str, float, str]]) -> float:
        """Score from 0.0-1.0 based on signal strength."""
        if not strategy_results:
            return 0.0
        
        valid_confidences = [conf for rec, conf, reason in strategy_results if conf >= 0.5]
        missing_data_count = sum(1 for rec, conf, reason in strategy_results if conf < 0.5)
        
        if missing_data_count >= len(strategy_results) * 0.67:
            return 0.2
        
        if not valid_confidences:
            return 0.2
        
        avg_confidence = sum(valid_confidences) / len(valid_confidences)
        
        if avg_confidence < 0.55:
            avg_confidence *= 0.8
        
        rsi = indicators.get('rsi')
        rsi_boost = 0.0
        if rsi is not None:
            if rsi < 25 or rsi > 75:
                rsi_boost = 0.2
            elif rsi < 30 or rsi > 70:
                rsi_boost = 0.1
        
        pb = metrics.get('price_to_book')
        pb_boost = 0.0
        if pb is not None:
            if pb < 0.5 or pb > 5.0:
                pb_boost = 0.2
            elif pb < 1.0 or pb > 3.0:
                pb_boost = 0.1
        
        signal_strength = avg_confidence + min(0.3, rsi_boost + pb_boost)
        
        return min(1.0, signal_strength)
    
    def _calculate_strategy_agreement(self, strategy_results: List[Tuple[str, float, str]], 
                                     final_recommendation: str) -> float:
        """Score from 0.0-1.0 based on strategy agreement."""
        if not strategy_results:
            return 0.0
        
        valid_recommendations = [rec for rec, conf, reason in strategy_results if conf >= 0.5]
        missing_data_count = sum(1 for rec, conf, reason in strategy_results if conf < 0.5)
        
        if missing_data_count >= len(strategy_results) * 0.67:
            return 0.2
        
        if not valid_recommendations:
            return 0.2
        
        agreement_count = sum(1 for rec in valid_recommendations if rec == final_recommendation)
        total_count = len(valid_recommendations)
        
        agreement_ratio = agreement_count / total_count if total_count > 0 else 0.0
        
        if total_count < len(strategy_results) * 0.5:
            agreement_ratio *= 0.7
        
        if agreement_count == total_count and total_count >= 2:
            agreement_ratio = min(1.0, agreement_ratio + 0.2)
        
        rec_counts = Counter(valid_recommendations)
        if len(rec_counts) > 1:
            if 'Buy' in rec_counts and 'Sell' in rec_counts:
                agreement_ratio *= 0.5
            elif agreement_ratio < 0.67:
                agreement_ratio *= 0.8
        
        return agreement_ratio

