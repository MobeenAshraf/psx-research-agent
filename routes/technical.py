"""Technical analysis routes."""

from typing import Dict, Any, List
import logging
from technical.data.price_repository import WebPriceRepository
from technical.analyzer import TechnicalAnalyzer
from technical.recommendation_engine import RecommendationEngine
from models.stock_analysis import StockAnalysis
from routes.helpers import normalize_indicators, format_detailed_analysis
from financial.services.index_membership_service import get_index_service


def get_technical_analysis(symbol: str) -> Dict[str, Any]:
    """Get technical analysis for a stock symbol."""
    try:
        symbol_upper = symbol.upper()
        price_repo = WebPriceRepository()
        technical_analyzer = TechnicalAnalyzer()
        
        historical = price_repo.get_historical_prices(symbol_upper, days=365)
        if not historical:
            return {
                'symbol': symbol_upper,
                'status': 'error',
                'error': 'No historical price data available'
            }
        
        indicators = _calculate_all_indicators(technical_analyzer, price_repo, symbol_upper, historical)
        signals, candlestick_patterns = _generate_all_signals(technical_analyzer, indicators, historical)
        metrics = _get_financial_metrics(symbol_upper)
        analysis = _create_stock_analysis(symbol_upper, indicators, metrics, signals, candlestick_patterns)
        
        return _format_analysis_response(analysis)
    except Exception as e:
        return {
            'symbol': symbol.upper(),
            'status': 'error',
            'error': str(e)
        }


def _calculate_all_indicators(technical_analyzer, price_repo, symbol_upper, historical):
    """Calculate all technical indicators."""
    indicators = technical_analyzer.calculate_indicators(historical)
    
    if historical:
        current_price = historical[-1]['close']
    else:
        current_price = price_repo.get_current_price(symbol_upper)
    
    if current_price:
        indicators['current_price'] = current_price
    
    index_service = get_index_service()
    index_membership = index_service.get_index_membership(symbol_upper)
    indicators['index_membership'] = index_membership
    
    return indicators


def _generate_all_signals(technical_analyzer, indicators, historical):
    """Generate all trading signals and patterns."""
    signals = technical_analyzer.generate_signals(indicators)
    
    candlestick_patterns = []
    if hasattr(technical_analyzer, 'get_candlestick_patterns'):
        if historical:
            candlestick_patterns = technical_analyzer.get_candlestick_patterns(historical)
    
    return signals, candlestick_patterns


def _get_financial_metrics(symbol_upper):
    """Get financial metrics if available."""
    return {}


def _consolidate_semantic_duplicates(signals: List[str]) -> List[str]:
    """Remove semantic duplicates from signals list."""
    consolidated = []
    seen_patterns = {
        'rsi_oversold': False,
        'rsi_overbought': False,
        'macd_bullish': False,
        'macd_bearish': False,
    }
    
    for signal in signals:
        signal_lower = signal.lower()
        
        if 'rsi' in signal_lower and 'oversold' in signal_lower:
            if 'near' not in signal_lower and not seen_patterns['rsi_oversold']:
                consolidated.append('Oversold (RSI < 30)')
                seen_patterns['rsi_oversold'] = True
            elif 'near' in signal_lower and signal not in consolidated:
                consolidated.append(signal)
        elif 'rsi' in signal_lower and 'overbought' in signal_lower:
            if 'near' not in signal_lower and not seen_patterns['rsi_overbought']:
                consolidated.append('Overbought (RSI > 70)')
                seen_patterns['rsi_overbought'] = True
            elif 'near' in signal_lower and signal not in consolidated:
                consolidated.append(signal)
        elif 'macd' in signal_lower and 'bullish' in signal_lower:
            if not seen_patterns['macd_bullish']:
                consolidated.append('Bullish MACD crossover')
                seen_patterns['macd_bullish'] = True
        elif 'macd' in signal_lower and 'bearish' in signal_lower:
            if not seen_patterns['macd_bearish']:
                consolidated.append('Bearish MACD crossover')
                seen_patterns['macd_bearish'] = True
        else:
            if signal not in consolidated:
                consolidated.append(signal)
    
    return consolidated


def _create_stock_analysis(symbol_upper, indicators, metrics, signals, candlestick_patterns):
    """Create StockAnalysis object with recommendation."""
    unique_signals = list(set(signals))
    consolidated_signals = _consolidate_semantic_duplicates(unique_signals)
    
    reasoning = []
    if consolidated_signals:
        reasoning.append("Technical Indicators:")
        for signal in consolidated_signals:
            reasoning.append(f"  • {signal}")
    
    if candlestick_patterns:
        if not reasoning:
            reasoning.append("Candlestick Patterns:")
        else:
            reasoning.append("")
            reasoning.append("Candlestick Patterns:")
        for pattern in candlestick_patterns:
            reasoning.append(f"  • {pattern}")
    
    recommendation_engine = RecommendationEngine()
    recommendation, confidence, strategy_reasoning = recommendation_engine.generate_recommendation(
        indicators, metrics, consolidated_signals
    )
    
    if strategy_reasoning:
        if reasoning:
            reasoning.append("")
        reasoning.append("Strategy Analysis:")
        for reason in strategy_reasoning:
            reasoning.append(f"  • {reason}")
    
    normalized_indicators = normalize_indicators(indicators)
    actionable_guidance = recommendation_engine.generate_actionable_guidance(
        recommendation, confidence, normalized_indicators, metrics, consolidated_signals
    )
    
    if actionable_guidance:
        reasoning.append("")
        for action in actionable_guidance:
            reasoning.append(action)
    
    return StockAnalysis(
        symbol=symbol_upper,
        indicators=indicators,
        metrics=metrics,
        recommendation=recommendation,
        confidence=confidence,
        reasoning=reasoning
    )


def _format_analysis_response(analysis):
    """Format analysis result for API response."""
    try:
        detailed_format = format_detailed_analysis(analysis)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error formatting detailed analysis: {e}", exc_info=True)
        detailed_format = f"Error generating detailed format: {str(e)}"
    
    return {
        'symbol': analysis.symbol,
        'recommendation': analysis.recommendation,
        'confidence': analysis.confidence,
        'indicators': analysis.indicators,
        'reasoning': analysis.reasoning,
        'detailed_format': detailed_format,
        'status': 'success'
    }

