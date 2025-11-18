"""FastAPI routes for PSX Stock Analysis."""

import json
import os
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
from price_repository import WebPriceRepository
from technical.analyzer import TechnicalAnalyzer
from financial.analyzers import FinancialAnalyzer
from technical.recommendation_engine import RecommendationEngine
from models.stock_analysis import StockAnalysis
from financial.langgraph.analyzer import LangGraphAnalyzer
from financial.repositories import FileResultRepository
from financial.services import (
    FinancialService,
    FinancialStatementAnalyzerService,
    PDFDownloadService,
    StatementNameGenerator,
)
from financial.pdfplumber_extractor import PDFPlumberExtractor
from state_monitor import stream_states, get_current_states


_executor = ThreadPoolExecutor(max_workers=2)


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
    current_price = price_repo.get_current_price(symbol_upper)
    if current_price:
        indicators['current_price'] = current_price
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
    metrics = {}
    try:
        financial_analyzer = FinancialAnalyzer()
        financial_data = financial_analyzer.analyze_report(symbol_upper)
        if financial_data:
            metrics = financial_analyzer.extract_metrics(financial_data)
    except Exception:
        pass
    return metrics


def _create_stock_analysis(symbol_upper, indicators, metrics, signals, candlestick_patterns):
    """Create StockAnalysis object with recommendation."""
    reasoning = list(signals) + candlestick_patterns
    
    recommendation_engine = RecommendationEngine()
    recommendation, confidence, recommendation_reasoning = recommendation_engine.generate_recommendation(
        indicators, metrics, signals
    )
    
    if recommendation_reasoning:
        reasoning.extend(recommendation_reasoning)
    
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


def _create_financial_analyzer():
    """Create financial statement analyzer service."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    return FinancialStatementAnalyzerService(
        financial_service=FinancialService(),
        pdf_download_service=PDFDownloadService(base_dir=Path("data/financial_statements")),
        pdf_extractor=PDFPlumberExtractor(),
        llm_client=LangGraphAnalyzer(api_key=api_key),
        result_repository=FileResultRepository(base_dir=Path("data/results")),
        stock_price_service=WebPriceRepository(),
    )


def check_latest_report(symbol: str) -> Dict[str, Any]:
    """Check for cached analysis results."""
    try:
        symbol_upper = symbol.upper()
        analyzer = _create_financial_analyzer()
        report = analyzer.financial_service.get_latest_report(symbol_upper)

        if not report or not report.report_url:
            return {
                "symbol": symbol_upper,
                "status": "no_report",
                "message": "No financial report found",
            }

        statement_name = StatementNameGenerator.generate_name(
            report.report_type, report.period_ended
        )

        if analyzer.result_repository.has_result(symbol_upper, statement_name):
            cached_result = analyzer.result_repository.get_result(
                symbol_upper, statement_name
            )
            states = _get_existing_states(symbol_upper)
            return {
                "symbol": symbol_upper,
                "status": "exists",
                "statement_name": statement_name,
                "result": cached_result,
                "states": states,
            }

        return {
            "symbol": symbol_upper,
            "status": "not_found",
            "message": "Report exists but analysis not found",
        }
    except Exception as exc:
        return {"symbol": symbol.upper(), "status": "error", "error": str(exc)}


def run_financial_analysis(
    symbol: str, pdf_text: Optional[str] = None, pdf_url: Optional[str] = None
) -> Dict[str, Any]:
    """Start financial analysis in background."""
    del pdf_text, pdf_url

    try:
        symbol_upper = symbol.upper()
        result_dir = Path("data/results") / symbol_upper
        if result_dir.exists():
            shutil.rmtree(result_dir)

        def run_analysis():
            analyzer = _create_financial_analyzer()
            analyzer.analyze_stock(symbol_upper)

        _executor.submit(run_analysis)
        return {
            "symbol": symbol_upper,
            "status": "started",
            "message": "Analysis started in background",
        }
    except Exception as exc:
        return {"symbol": symbol.upper(), "status": "error", "error": str(exc)}


def _get_existing_states(symbol: str) -> Dict[str, Any]:
    """Get existing state files for a symbol."""
    states_dir = Path("data/results") / symbol.upper() / "states"
    
    if not states_dir.exists():
        return {}
    
    states = {}
    state_files = sorted(states_dir.glob("*_state.json"))
    
    for state_file in state_files:
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                step_name = state_file.stem.replace('_state', '')
                states[step_name] = state_data
        except Exception:
            continue
    
    return states

