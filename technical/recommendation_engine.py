from typing import Dict, Any, Tuple, List
from technical.recommendation.rsi_strategy import RSIStrategy
from technical.recommendation.macd_strategy import MACDStrategy
from technical.recommendation.valuation_strategy import ValuationStrategy
from technical.confidence_calculator import ConfidenceCalculator


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
    
    def generate_actionable_guidance(
        self,
        recommendation: str,
        confidence: float,
        indicators: Dict[str, Any],
        metrics: Dict[str, Any],
        signals: List[str]
    ) -> List[str]:
        """Generate clear actionable guidance based on analysis."""
        actions = []
        
        current_price = indicators.get('current_price')
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        trend = indicators.get('trend')
        volume_ratio = indicators.get('volume_ratio')
        support = indicators.get('support')
        resistance = indicators.get('resistance')
        
        if recommendation == 'Buy':
            actions.append(f"BUY RECOMMENDATION (Confidence: {confidence:.0%})")
            actions.append("")
            
            if current_price and support:
                stop_loss_pct = ((current_price - support) / current_price) * 100
                if stop_loss_pct > 0:
                    actions.append(f"• Set stop-loss at {support:.2f} ({stop_loss_pct:.1f}% below current price)")
            
            if current_price and resistance:
                target_pct = ((resistance - current_price) / current_price) * 100
                if target_pct > 0:
                    actions.append(f"• Consider taking profits near {resistance:.2f} ({target_pct:.1f}% above current price)")
            
            if rsi and rsi < 30:
                actions.append("• RSI indicates oversold condition - good entry opportunity")
            elif rsi and rsi < 40:
                actions.append("• RSI near oversold - monitor for confirmation")
            
            if macd and macd_signal and macd > macd_signal:
                actions.append("• MACD bullish crossover confirms upward momentum")
            
            if volume_ratio and volume_ratio > 1.5:
                actions.append("• High volume supports the buy signal - increased conviction")
            elif volume_ratio and volume_ratio < 0.5:
                actions.append("• Low volume - wait for volume confirmation before entering")
            
            if trend == 'Downtrend':
                actions.append("• CAUTION: Stock is in downtrend - consider waiting for trend reversal confirmation")
            
            actions.append("• Consider position sizing: Start with smaller position, add on confirmation")
            
        elif recommendation == 'Sell':
            actions.append(f"SELL RECOMMENDATION (Confidence: {confidence:.0%})")
            actions.append("")
            
            if current_price and support:
                actions.append(f"• Consider selling if price breaks below support at {support:.2f}")
            
            if rsi and rsi > 70:
                actions.append("• RSI indicates overbought condition - profit-taking opportunity")
            elif rsi and rsi > 60:
                actions.append("• RSI near overbought - monitor for exit signals")
            
            if macd and macd_signal and macd < macd_signal:
                actions.append("• MACD bearish crossover indicates weakening momentum")
            
            if trend == 'Uptrend':
                actions.append("• CAUTION: Stock is in uptrend - consider partial profit-taking rather than full exit")
            
            actions.append("• Consider selling in tranches: Sell 50% now, 50% on further weakness")
            
        else:
            actions.append(f"HOLD RECOMMENDATION (Confidence: {confidence:.0%})")
            actions.append("")
            actions.append("• No clear directional signal - maintain current position")
            
            bullish_count = sum(1 for s in signals if 'bullish' in s.lower() or 'oversold' in s.lower())
            bearish_count = sum(1 for s in signals if 'bearish' in s.lower() or 'overbought' in s.lower())
            
            if bullish_count > 0 and bearish_count > 0:
                actions.append("• Mixed signals detected - conflicting indicators suggest waiting for clarity")
            
            if rsi and 40 <= rsi <= 60:
                actions.append("• RSI in neutral zone - no extreme conditions")
            
            actions.append("• Monitor key levels: Watch for breakouts above resistance or breakdowns below support")
        
        return actions
