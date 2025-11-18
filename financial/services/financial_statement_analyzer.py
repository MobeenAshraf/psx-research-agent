"""Shared financial statement analyzer orchestration."""

from typing import Any, Dict, Optional

from financial.pdf_exceptions import (
    LLMAnalysisError,
    PDFDownloadError,
    PDFExtractionError,
)
from financial.pdfplumber_extractor import PDFPlumberExtractor
from financial.services.financial_service import FinancialService
from financial.services.pdf_download_service import PDFDownloadService
from financial.services.statement_name_generator import StatementNameGenerator
from financial.repositories.file_result_repository import FileResultRepository
from financial.langgraph.analyzer import LangGraphAnalyzer


class FinancialStatementAnalyzerService:
    """Download, extract, and analyze financial statements using LangGraph."""

    def __init__(
        self,
        financial_service: Optional[FinancialService] = None,
        pdf_download_service: Optional[PDFDownloadService] = None,
        pdf_extractor: Optional[PDFPlumberExtractor] = None,
        llm_client: Optional[LangGraphAnalyzer] = None,
        result_repository: Optional[FileResultRepository] = None,
        stock_price_service: Optional[Any] = None,
    ):
        self.financial_service = financial_service or FinancialService()
        self.pdf_download_service = pdf_download_service or PDFDownloadService()
        self.pdf_extractor = pdf_extractor or PDFPlumberExtractor()
        self.llm_client = llm_client or LangGraphAnalyzer()
        self.result_repository = result_repository or FileResultRepository()
        self.stock_price_service = stock_price_service

    def analyze_stock(
        self, symbol: str, pre_fetched_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Analyze the latest report for a symbol."""
        report = self.financial_service.get_latest_report(symbol)
        if not report or not report.report_url:
            return {
                "symbol": symbol,
                "status": "no_report",
                "message": "No financial report found",
            }

        statement_name = StatementNameGenerator.generate_name(
            report.report_type, report.period_ended
        )
        if self.result_repository.has_result(symbol, statement_name):
            cached = self.result_repository.get_result(symbol, statement_name)
            return {
                "symbol": symbol,
                "status": "cached",
                "statement_name": statement_name,
                "result": cached,
            }

        try:
            result = self._process_pdf(report, pre_fetched_price=pre_fetched_price)
            self.result_repository.save_result(symbol, statement_name, result)
            return {
                "symbol": symbol,
                "status": "analyzed",
                "statement_name": statement_name,
                "result": result,
            }
        except (PDFDownloadError, PDFExtractionError, LLMAnalysisError) as exc:
            return {"symbol": symbol, "status": "error", "error": str(exc)}

    def _process_pdf(self, report, pre_fetched_price: Optional[float] = None) -> str:
        pdf_path = self.pdf_download_service.download_pdf(
            report.report_url, report.symbol
        )
        pdf_text = self.pdf_extractor.extract_text(pdf_path)

        if not pdf_text or not pdf_text.strip():
            raise PDFExtractionError(
                f"PDF extraction returned empty text for {report.symbol}."
            )
        if len(pdf_text.strip()) < 100:
            raise PDFExtractionError(
                f"PDF extraction returned very short text for {report.symbol}."
            )

        stock_price = pre_fetched_price
        if stock_price is None and self.stock_price_service:
            try:
                stock_price = self.stock_price_service.get_current_price(report.symbol)
            except Exception:
                stock_price = None

        currency = self._detect_currency(pdf_text)
        return self.llm_client.analyze(
            pdf_text=pdf_text,
            stock_price=stock_price,
            currency=currency,
            symbol=report.symbol,
        )

    @staticmethod
    def _detect_currency(pdf_text: str) -> str:
        pdf_upper = pdf_text.upper()
        if "PKR" in pdf_upper or "PAKISTAN" in pdf_upper:
            return "PKR"
        if "USD" in pdf_upper or "$" in pdf_text:
            return "USD"
        if "EUR" in pdf_upper or "€" in pdf_text:
            return "EUR"
        if "GBP" in pdf_upper or "£" in pdf_text:
            return "GBP"
        return ""


