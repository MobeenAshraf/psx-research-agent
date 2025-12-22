"""Financial analysis routes."""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from technical.price_repository import WebPriceRepository
from financial.langgraph.analyzer import LangGraphAnalyzer
from financial.repositories import FileResultRepository
from financial.services import (
    FinancialService,
    FinancialStatementAnalyzerService,
    PDFDownloadService,
    StatementNameGenerator,
)
from financial.config.model_config import ModelConfig


_executor = ThreadPoolExecutor(max_workers=2)


def _create_financial_analyzer():
    """Create financial statement analyzer service."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    return FinancialStatementAnalyzerService(
        financial_service=FinancialService(),
        pdf_download_service=PDFDownloadService(base_dir=Path("data/financial_statements")),
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

