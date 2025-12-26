"""Technical analysis routes."""

import logging
from typing import Any, Dict, List, Optional

from financial.services.index_membership_service import get_index_service
from financial.services.stock_page_service import get_stock_page_service
from models.stock_analysis import StockAnalysis
from routes.helpers import format_detailed_analysis, normalize_indicators
from technical.analyzer import TechnicalAnalyzer
from technical.price_repository import WebPriceRepository
from technical.recommendation_engine import RecommendationEngine

_logger = logging.getLogger(__name__)


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


def _get_financial_metrics(symbol_upper: str) -> Dict[str, Any]:
    """Get financial metrics from stock page data if available and valid."""
    metrics: Dict[str, Any] = {}

    try:
        stock_page_service = get_stock_page_service()
        stock_page_data = stock_page_service.fetch_stock_financials(symbol_upper)

        if stock_page_data is None or not stock_page_data.is_valid:
            _logger.info(
                f"Stock page data not available or invalid for {symbol_upper}"
            )
            return metrics

        latest_annual = stock_page_service.get_latest_annual_data(stock_page_data)
        if latest_annual:
            annual_metrics = latest_annual.get("metrics", {})
            annual_ratios = latest_annual.get("ratios", {})

            if annual_metrics.get("eps") is not None:
                metrics["eps"] = annual_metrics["eps"]
            if annual_metrics.get("sales") is not None:
                metrics["sales"] = annual_metrics["sales"]
            if annual_metrics.get("profit_after_tax") is not None:
                metrics["profit_after_tax"] = annual_metrics["profit_after_tax"]

            if annual_ratios.get("net_profit_margin") is not None:
                metrics["net_profit_margin"] = annual_ratios["net_profit_margin"]
            if annual_ratios.get("eps_growth") is not None:
                metrics["eps_growth"] = annual_ratios["eps_growth"]
            if annual_ratios.get("peg") is not None:
                metrics["peg"] = annual_ratios["peg"]
            if annual_ratios.get("gross_profit_margin") is not None:
                metrics["gross_profit_margin"] = annual_ratios["gross_profit_margin"]

            metrics["annual_year"] = latest_annual.get("year")

        latest_quarterly = stock_page_service.get_latest_quarterly_data(stock_page_data)
        if latest_quarterly:
            quarterly_metrics = latest_quarterly.get("metrics", {})

            if quarterly_metrics.get("eps") is not None:
                metrics["quarterly_eps"] = quarterly_metrics["eps"]
            if quarterly_metrics.get("sales") is not None:
                metrics["quarterly_sales"] = quarterly_metrics["sales"]
            if quarterly_metrics.get("profit_after_tax") is not None:
                metrics["quarterly_profit"] = quarterly_metrics["profit_after_tax"]

            metrics["quarterly_period"] = latest_quarterly.get("period")

        metrics["stock_page_data_valid"] = True

        _logger.info(f"Fetched financial metrics for {symbol_upper}: {list(metrics.keys())}")

    except Exception as exc:
        _logger.warning(f"Failed to fetch financial metrics for {symbol_upper}: {exc}")

    return metrics


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

