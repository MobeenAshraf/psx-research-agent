"""Handler for financial analysis requests."""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, Optional

_executor = ThreadPoolExecutor(max_workers=2)


def create_financial_analyzer():
    """Create financial statement analyzer service."""
    import os
    from psx_analysis.financial_analysis.langgraph.analyzer import LangGraphAnalyzer
    from psx_analysis.financial_analysis.repositories import FileResultRepository
    from psx_analysis.financial_analysis.services import (
        FinancialService,
        FinancialStatementAnalyzerService,
        PDFDownloadService,
    )
    from psx_analysis.financial_analysis.pdfplumber_extractor import PDFPlumberExtractor
    from psx_web.handlers.price_repository import WebPriceRepository

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
    """Check for cached analysis results using shared services."""
    try:
        from psx_analysis.financial_analysis.services import StatementNameGenerator

        symbol_upper = symbol.upper()
        analyzer = create_financial_analyzer()
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
    del pdf_text, pdf_url  # handled internally by analyzer

    try:
        symbol_upper = symbol.upper()
        result_dir = Path("data/results") / symbol_upper
        if result_dir.exists():
            shutil.rmtree(result_dir)

        def run_analysis():
            analyzer = create_financial_analyzer()
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
            import json
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                step_name = state_file.stem.replace('_state', '')
                states[step_name] = state_data
        except Exception:
            continue
    
    return states
