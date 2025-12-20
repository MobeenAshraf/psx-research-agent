"""FastAPI routes for PSX Stock Analysis."""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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
from financial.config.user_profile_loader import UserProfileLoader
from financial.config.model_config import ModelConfig
from financial.langgraph.decision_llm_helper import DecisionLLMHelper
from financial.langgraph.api_client import OpenRouterAPIClient


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
    
    if historical:
        current_price = historical[-1]['close']
    else:
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
    
    normalized_indicators = _normalize_indicators(indicators)
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


def check_latest_report(
    symbol: str,
    extraction_model: Optional[str] = "auto",
    analysis_model: Optional[str] = "auto"
) -> Dict[str, Any]:
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

        from financial.config.model_config import ModelConfig
        normalized_extraction = ModelConfig.normalize_model_name(extraction_model, is_extraction=True)
        normalized_analysis = ModelConfig.normalize_model_name(analysis_model, is_extraction=False)

        if analyzer.result_repository.has_result(
            symbol_upper, statement_name,
            extraction_model=normalized_extraction,
            analysis_model=normalized_analysis
        ):
            cached_result = analyzer.result_repository.get_result(
                symbol_upper, statement_name,
                extraction_model=normalized_extraction,
                analysis_model=normalized_analysis
            )
            states = _get_existing_states(
                symbol_upper,
                extraction_model=normalized_extraction,
                analysis_model=normalized_analysis
            )
            final_state = states.get("99_final", {})
            return {
                "symbol": symbol_upper,
                "status": "exists",
                "statement_name": statement_name,
                "result": cached_result,
                "states": states,
                "token_usage": final_state.get("token_usage"),
            }

        return {
            "symbol": symbol_upper,
            "status": "not_found",
            "message": "Report exists but analysis not found",
        }
    except Exception as exc:
        return {"symbol": symbol.upper(), "status": "error", "error": str(exc)}


def run_financial_analysis(
    symbol: str,
    pdf_text: Optional[str] = None,
    pdf_url: Optional[str] = None,
    extraction_model: Optional[str] = "auto",
    analysis_model: Optional[str] = "auto",
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Start financial analysis in background."""
    del pdf_text, pdf_url

    try:
        symbol_upper = symbol.upper()

        def run_analysis():
            analyzer = _create_financial_analyzer()
            analyzer.analyze_stock(
                symbol_upper,
                extraction_model=extraction_model,
                analysis_model=analysis_model,
                user_profile=user_profile
            )

        _executor.submit(run_analysis)
        return {
            "symbol": symbol_upper,
            "status": "started",
            "message": "Analysis started in background",
        }
    except Exception as exc:
        return {"symbol": symbol.upper(), "status": "error", "error": str(exc)}


def _generate_model_key(
    extraction_model: Optional[str] = None, analysis_model: Optional[str] = None
) -> str:
    """Generate model key for directory naming (same logic as FileResultRepository)."""
    import re
    extraction = extraction_model or "default"
    analysis = analysis_model or "default"
    
    model_key = f"{extraction}_{analysis}"
    model_key = model_key.replace("/", "_")
    model_key = re.sub(r'[^a-zA-Z0-9_-]', '_', model_key)
    model_key = re.sub(r'_+', '_', model_key)
    model_key = model_key.strip('_')
    
    return model_key


def _get_existing_states(
    symbol: str,
    extraction_model: Optional[str] = None,
    analysis_model: Optional[str] = None
) -> Dict[str, Any]:
    """Get existing state files for a symbol and model combination."""
    base_dir = Path("data/results") / symbol.upper()
    
    if extraction_model or analysis_model:
        model_key = _generate_model_key(extraction_model, analysis_model)
        states_dir = base_dir / model_key / "states"
    else:
        states_dir = base_dir / "states"
    
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


def get_llm_decision(
    symbol: str,
    extraction_model: Optional[str] = "auto",
    analysis_model: Optional[str] = "auto",
    decision_model: Optional[str] = "auto"
) -> Dict[str, Any]:
    """
    Get LLM decision combining user profile, technical analysis, and financial analysis.
    
    Args:
        symbol: Stock symbol
        extraction_model: Model for extraction (used to find cached financial analysis)
        analysis_model: Model for analysis (used to find cached financial analysis)
        decision_model: Model for decision-making
        
    Returns:
        Dictionary with decision, confidence, reasoning, etc.
    """
    try:
        symbol_upper = symbol.upper()
        
        # Load user profile
        try:
            user_profile = UserProfileLoader.load_profile()
        except (FileNotFoundError, ValueError) as e:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Failed to load user profile: {str(e)}"
            }
        
        # Get technical analysis
        try:
            technical_analysis = get_technical_analysis(symbol_upper)
            if technical_analysis.get("status") == "error":
                return {
                    "symbol": symbol_upper,
                    "status": "error",
                    "error": f"Technical analysis failed: {technical_analysis.get('error', 'Unknown error')}"
                }
        except Exception as e:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Failed to get technical analysis: {str(e)}"
            }
        
        # Get financial analysis
        financial_result = check_latest_report(symbol_upper, extraction_model, analysis_model)
        if financial_result.get("status") not in ["exists", "not_found"]:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Financial analysis check failed: {financial_result.get('message', 'Unknown error')}"
            }
        
        if financial_result.get("status") == "not_found":
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "Financial analysis not found. Please run financial analysis first."
            }
        
        # Get final report from states (use normalized models to match the cached result)
        normalized_extraction = ModelConfig.normalize_model_name(extraction_model, is_extraction=True)
        normalized_analysis = ModelConfig.normalize_model_name(analysis_model, is_extraction=False)
        states = _get_existing_states(
            symbol_upper,
            extraction_model=normalized_extraction,
            analysis_model=normalized_analysis
        )
        final_state = states.get("99_final", {})
        financial_report = final_state.get("final_report", "")
        
        if not financial_report:
            financial_report = financial_result.get("result", "")
        
        if not financial_report:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "Financial analysis report not available"
            }
        
        # Build prompt summaries
        user_profile_summary = json.dumps(user_profile, indent=2)
        
        technical_summary = f"""
Symbol: {symbol_upper}
Recommendation: {technical_analysis.get('recommendation', 'N/A')}
Confidence: {technical_analysis.get('confidence', 0):.2f}
Key Indicators: {json.dumps(technical_analysis.get('indicators', {}), indent=2)}
Reasoning: {json.dumps(technical_analysis.get('reasoning', []), indent=2)}
"""
        
        financial_summary = financial_report[:2000] if len(financial_report) > 2000 else financial_report
        
        # Load decision prompt and schema
        prompt_dir = Path(__file__).resolve().parents[0] / "financial" / "prompts"
        decision_prompt_path = prompt_dir / "decision_prompt.md"
        schema_path = prompt_dir / "decision_response_schema.json"
        
        if not decision_prompt_path.exists():
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Decision prompt file not found: {decision_prompt_path}"
            }
        
        if not schema_path.exists():
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Decision schema file not found: {schema_path}"
            }
        
        system_prompt_template = decision_prompt_path.read_text(encoding='utf-8')
        schema_content = schema_path.read_text(encoding='utf-8')
        
        # Replace placeholders in prompt
        system_prompt = system_prompt_template.replace("{SCHEMA_PLACEHOLDER}", schema_content)
        system_prompt = system_prompt.replace("{USER_PROFILE_PLACEHOLDER}", user_profile_summary)
        system_prompt = system_prompt.replace("{TECHNICAL_ANALYSIS_SUMMARY_PLACEHOLDER}", technical_summary)
        system_prompt = system_prompt.replace("{FINANCIAL_ANALYSIS_SUMMARY_PLACEHOLDER}", financial_summary)
        
        user_prompt = f"Analyze stock {symbol_upper} and provide your investment decision."
        
        # Get decision model
        decision_model_actual = ModelConfig.get_decision_model(decision_model)
        
        # Call decision LLM
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "OPENROUTER_API_KEY environment variable is required"
            }
        
        api_client = OpenRouterAPIClient(api_key)
        decision_helper = DecisionLLMHelper(api_client)
        
        decision_result, token_usage = decision_helper.call_decision_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=decision_model_actual
        )
        
        return {
            "symbol": symbol_upper,
            "status": "success",
            "decision": decision_result.get("decision"),
            "confidence": decision_result.get("confidence"),
            "summary": decision_result.get("summary"),
            "reasons": decision_result.get("reasons", []),
            "risk_notes": decision_result.get("risk_notes", []),
            "dividend_analysis": decision_result.get("dividend_analysis"),
            "halal_compliance": decision_result.get("halal_compliance"),
            "raw_response": json.dumps(decision_result, indent=2),
            "token_usage": token_usage
        }
        
    except Exception as exc:
        return {
            "symbol": symbol.upper(),
            "status": "error",
            "error": str(exc)
        }

