from typing import Dict, Any, Tuple, List
from technical.recommendation.rsi_strategy import RSIStrategy
from technical.recommendation.macd_strategy import MACDStrategy
from technical.confidence_calculator import ConfidenceCalculator


class RecommendationEngine:
    def __init__(self):
        self.strategies = [
            RSIStrategy(),
            MACDStrategy(),
        ]
        self.confidence_calculator = ConfidenceCalculator()
    
    def generate_recommendation(
        self,
        indicators: Dict[str, Any],
        metrics: Dict[str, Any],
        signals: List[str]
    ) -> Tuple[str, float, List[str]]:
        strategy_results = [strategy.evaluate(indicators, metrics) for strategy in self.strategies]
        reasoning = [reason for _, _, reason in strategy_results]
        directions = {direction for direction, _, _ in strategy_results if direction != "Hold"}
        recommendation = "Hold"
        if indicators.get("price_data_stale"):
            reasoning.append("Last available price is stale")
        elif indicators.get("current_volume") == 0:
            reasoning.append("No trades in the latest session")
        elif len(directions) > 1:
            reasoning.append("RSI and MACD indicate opposing directions")
        elif directions:
            direction = next(iter(directions))
            opposing_trend = {"Buy": "Downtrend", "Sell": "Uptrend"}[direction]
            if indicators.get("trend") == opposing_trend:
                reasoning.append(f"{direction} signal conflicts with the prevailing trend")
            else:
                recommendation = direction

        strength = self.confidence_calculator.calculate_confidence(
            strategy_results, indicators, recommendation
        )
        return recommendation, strength, reasoning

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
        crossover = indicators.get('macd_crossover')
        trend = indicators.get('trend')
        volume_ratio = indicators.get('volume_ratio')
        support = indicators.get('support')
        resistance = indicators.get('resistance')
        
        if recommendation == 'Buy':
            actions.append(f"BUY RECOMMENDATION (Signal strength: {confidence:.0%})")
            actions.append("")
            
            if current_price and support:
                stop_loss_pct = ((current_price - support) / current_price) * 100
                if stop_loss_pct > 0:
                    actions.append(f"• Set stop-loss at {support:.2f} ({stop_loss_pct:.1f}% below current price)")
            
            if current_price and resistance:
                target_pct = ((resistance - current_price) / current_price) * 100
                if target_pct > 0:
                    actions.append(f"• Consider taking profits near {resistance:.2f} ({target_pct:.1f}% above current price)")
            
            if rsi is not None and rsi < 30:
                actions.append("• RSI indicates oversold condition - good entry opportunity")
            elif rsi is not None and rsi < 40:
                actions.append("• RSI near oversold - monitor for confirmation")
            
            if crossover == 'bullish':
                actions.append("• MACD bullish crossover confirms upward momentum")
            
            if volume_ratio is not None and volume_ratio > 1.5:
                actions.append("• High volume supports the buy signal - increased conviction")
            elif volume_ratio is not None and volume_ratio < 0.5:
                actions.append("• Low volume - wait for volume confirmation before entering")
            
            if trend == 'Downtrend':
                actions.append("• CAUTION: Stock is in downtrend - consider waiting for trend reversal confirmation")
            
            actions.append("• Consider position sizing: Start with smaller position, add on confirmation")
            
        elif recommendation == 'Sell':
            actions.append(f"SELL RECOMMENDATION (Signal strength: {confidence:.0%})")
            actions.append("")
            
            if current_price and support:
                actions.append(f"• Consider selling if price breaks below support at {support:.2f}")
            
            if rsi is not None and rsi > 70:
                actions.append("• RSI indicates overbought condition - profit-taking opportunity")
            elif rsi is not None and rsi > 60:
                actions.append("• RSI near overbought - monitor for exit signals")
            
            if crossover == 'bearish':
                actions.append("• MACD bearish crossover indicates weakening momentum")
            
            if trend == 'Uptrend':
                actions.append("• CAUTION: Stock is in uptrend - consider partial profit-taking rather than full exit")
            
            actions.append("• Consider selling in tranches: Sell 50% now, 50% on further weakness")
            
        else:
            actions.append(f"HOLD RECOMMENDATION (Signal strength: {confidence:.0%})")
            actions.append("")
            actions.append("• No clear directional signal - maintain current position")
            
            bullish_count = sum(1 for s in signals if 'bullish' in s.lower() or 'oversold' in s.lower())
            bearish_count = sum(1 for s in signals if 'bearish' in s.lower() or 'overbought' in s.lower())
            
            if bullish_count > 0 and bearish_count > 0:
                actions.append("• Mixed signals detected - conflicting indicators suggest waiting for clarity")
            
            if rsi is not None and 40 <= rsi <= 60:
                actions.append("• RSI in neutral zone - no extreme conditions")
            
            actions.append("• Monitor key levels: Watch for breakouts above resistance or breakdowns below support")
        
        return actions
