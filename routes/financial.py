"""Financial analysis routes."""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from financial.result_paths import DEFAULT_RESULTS_DIRECTORY, model_directory
from state_monitor import read_states
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
from financial.config.cost_calculator import calculate_cost


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
        result_repository=FileResultRepository(base_dir=DEFAULT_RESULTS_DIRECTORY),
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

        if analyzer.result_repository.has_valid_analysis(
            symbol_upper, statement_name, report.report_url, normalized_extraction, normalized_analysis
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
            token_usage = final_state.get("token_usage")
            
            extraction_cost = 0.0
            analysis_cost = 0.0
            total_cost = 0.0
            
            if token_usage:
                steps = token_usage.get("steps", {})
                extract_step = steps.get("extract", {})
                analyze_step = steps.get("analyze", {})
                
                if extract_step:
                    extract_model = extract_step.get("model", normalized_extraction)
                    extraction_cost = calculate_cost(extract_step, extract_model)
                
                if analyze_step:
                    analyze_model = analyze_step.get("model", normalized_analysis)
                    analysis_cost = calculate_cost(analyze_step, analyze_model)
                
                total_cost = extraction_cost + analysis_cost
            
            return {
                "symbol": symbol_upper,
                "status": "exists",
                "statement_name": statement_name,
                "result": cached_result,
                "states": states,
                "token_usage": token_usage,
                "extraction_cost": extraction_cost,
                "analysis_cost": analysis_cost,
                "total_cost": total_cost,
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


def _get_existing_states(
    symbol: str,
    extraction_model: Optional[str] = None,
    analysis_model: Optional[str] = None
) -> Dict[str, Any]:
    """Get existing state files for a symbol and model combination."""
    base_dir = DEFAULT_RESULTS_DIRECTORY / symbol.upper()
    
    if extraction_model or analysis_model:
        model_key = model_directory(extraction_model, analysis_model)
        states_dir = base_dir / model_key / "states"
    else:
        states_dir = base_dir / "states"
    
    return read_states(states_dir)
