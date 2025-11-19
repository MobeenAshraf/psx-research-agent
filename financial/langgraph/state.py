"""State definition for LangGraph workflow."""

from typing import Dict, Any, Optional, TypedDict, List


class AnalysisState(TypedDict):
    """State for the financial analysis workflow."""
    pdf_text: str
    stock_price: Optional[float]
    currency: str
    extracted_data: Optional[Dict[str, Any]]
    calculated_metrics: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    final_report: Optional[str]
    errors: List[str]
    token_usage: Optional[Dict[str, Any]]

