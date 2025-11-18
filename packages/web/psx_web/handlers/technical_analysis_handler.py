"""Handler for technical analysis requests."""

from typing import Dict, Any
from psx_web.handlers.dependency_factory import DependencyFactory
from psx_analysis.domain.entities.stock_analysis import StockAnalysis


def _normalize_indicators(indicators: dict) -> dict:
    """Normalize indicators by converting pandas Series to scalars."""
    import pandas as pd
    
    normalized = indicators.copy()
    for key, value in list(normalized.items()):
        if isinstance(value, pd.Series):
            if not value.empty:
                normalized[key] = float(value.iloc[-1])
            else:
                normalized[key] = None
        elif isinstance(value, (list, tuple)) and len(value) > 0:
            normalized[key] = value[-1] if isinstance(value[-1], (int, float)) else value
        elif isinstance(value, dict):
            normalized[key] = value
        elif value is None or (isinstance(value, float) and pd.isna(value)):
            normalized[key] = None
    return normalized


def _format_detailed_analysis(analysis) -> str:
    """Format analysis for display."""
    normalized_indicators = _normalize_indicators(analysis.indicators)
    
    lines = [
        f"Symbol: {analysis.symbol}",
        f"Recommendation: {analysis.recommendation}",
        f"Confidence: {analysis.confidence:.2f}",
        "",
        "Indicators:",
    ]
    
    for key, value in normalized_indicators.items():
        if value is not None:
            lines.append(f"  {key}: {value}")
    
    if analysis.reasoning:
        lines.append("")
        lines.append("Reasoning:")
        for reason in analysis.reasoning:
            lines.append(f"  - {reason}")
    
    return "\n".join(lines)


def get_technical_analysis(symbol: str) -> Dict[str, Any]:
    """
    Get technical analysis for a stock symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'SYS', 'INDU')
        
    Returns:
        Dictionary with analysis results or error
    """
    try:
        symbol_upper = symbol.upper()
        price_repo = DependencyFactory.get_price_repository()
        analysis_repo = DependencyFactory.get_analysis_repository()
        technical_analyzer = DependencyFactory.get_technical_analyzer()
        financial_analyzer = DependencyFactory.get_financial_analyzer()
        recommendation_engine = DependencyFactory.get_recommendation_engine()
        
        historical = price_repo.get_historical_prices(symbol_upper, days=365)
        if not historical:
            return {
                'symbol': symbol_upper,
                'status': 'error',
                'error': 'No historical price data available'
            }
        
        indicators = technical_analyzer.calculate_indicators(historical)
        current_price = price_repo.get_current_price(symbol_upper)
        if current_price:
            indicators['current_price'] = current_price
        
        sheets_service = DependencyFactory.get_sheets_service()
        if sheets_service:
            try:
                stocks_data = sheets_service.get_stocks_with_action()
                stock_data = stocks_data.get(symbol_upper)
                if stock_data and stock_data.get('price'):
                    target_price = stock_data['price']
                    if target_price and target_price > 0:
                        indicators['target_price'] = float(target_price)
            except Exception:
                pass
        
        signals = technical_analyzer.generate_signals(indicators)
        
        candlestick_patterns = []
        if hasattr(technical_analyzer, 'get_candlestick_patterns'):
            if historical:
                candlestick_patterns = technical_analyzer.get_candlestick_patterns(historical)
        
        reasoning = list(signals) + candlestick_patterns
        
        metrics = {}
        try:
            financial_data = financial_analyzer.analyze_report(symbol_upper)
            if financial_data:
                metrics = financial_analyzer.extract_metrics(financial_data)
        except Exception:
            pass
        
        recommendation, confidence, recommendation_reasoning = recommendation_engine.generate_recommendation(
            indicators, metrics, signals
        )
        
        if recommendation_reasoning:
            reasoning.extend(recommendation_reasoning)
        
        analysis = StockAnalysis(
            symbol=symbol_upper,
            indicators=indicators,
            metrics=metrics,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning
        )
        
        analysis_repo.save(analysis)
        
        try:
            detailed_format = _format_detailed_analysis(analysis)
        except Exception as e:
            import logging
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
    except Exception as e:
        return {
            'symbol': symbol.upper(),
            'status': 'error',
            'error': str(e)
        }

