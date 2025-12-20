"""Shared financial statement analyzer orchestration."""

from typing import Any, Dict, Optional

import logging
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

_logger = logging.getLogger(__name__)


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
        self,
        symbol: str,
        pre_fetched_price: Optional[float] = None,
        extraction_model: Optional[str] = "auto",
        analysis_model: Optional[str] = "auto",
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze the latest report for a symbol."""
        from financial.config.model_config import ModelConfig
        
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
        
        normalized_extraction = ModelConfig.normalize_model_name(extraction_model, is_extraction=True)
        normalized_analysis = ModelConfig.normalize_model_name(analysis_model, is_extraction=False)
        
        if self.result_repository.has_result(
            symbol, statement_name,
            extraction_model=normalized_extraction,
            analysis_model=normalized_analysis
        ):
            cached = self.result_repository.get_result(
                symbol, statement_name,
                extraction_model=normalized_extraction,
                analysis_model=normalized_analysis
            )
            return {
                "symbol": symbol,
                "status": "cached",
                "statement_name": statement_name,
                "result": cached,
            }

        try:
            result = self._process_pdf(
                report,
                pre_fetched_price=pre_fetched_price,
                extraction_model=extraction_model,
                analysis_model=analysis_model,
                user_profile=user_profile
            )
            self.result_repository.save_result(
                symbol, statement_name, result,
                extraction_model=normalized_extraction,
                analysis_model=normalized_analysis
            )
            return {
                "symbol": symbol,
                "status": "analyzed",
                "statement_name": statement_name,
                "result": result,
            }
        except (PDFDownloadError, PDFExtractionError, LLMAnalysisError) as exc:
            return {"symbol": symbol, "status": "error", "error": str(exc)}

    def _process_pdf(
        self,
        report,
        pre_fetched_price: Optional[float] = None,
        extraction_model: Optional[str] = "auto",
        analysis_model: Optional[str] = "auto",
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        from financial.config.model_config import ModelConfig
        
        pdf_path = self.pdf_download_service.download_pdf(
            report.report_url, report.symbol
        )
        
        pdf_text = ""
        use_multimodal = False
        
        extraction_model_actual = ModelConfig.get_extraction_model(extraction_model)
        is_multimodal = ModelConfig.is_multimodal_model(extraction_model_actual)
        
        if is_multimodal:
            _logger.info(
                f"User selected Gemini model ({extraction_model_actual}) for {report.symbol}. "
                "Using multimodal PDF processing directly."
            )
            use_multimodal = True
            pdf_text = ""
        else:
            try:
                pdf_text = self.pdf_extractor.extract_text(pdf_path)
                _logger.info(f"Text extraction successful for {report.symbol}: {len(pdf_text)} characters")
            except PDFExtractionError as e:
                _logger.warning(f"Text extraction failed for {report.symbol}: {str(e)}")
                pdf_text = ""
            
            if not pdf_text or len(pdf_text.strip()) < 100:
                _logger.info(
                    f"PDF extraction returned insufficient text ({len(pdf_text)} chars) for {report.symbol}. "
                    "Falling back to multimodal PDF processing."
                )
                use_multimodal = True
                pdf_text = ""
        
        stock_price = pre_fetched_price
        if stock_price is None and self.stock_price_service:
            try:
                stock_price = self.stock_price_service.get_current_price(report.symbol)
            except Exception:
                stock_price = None

        if use_multimodal:
            currency = ""
            _logger.info(f"Using multimodal PDF processing for {report.symbol}")
            try:
                return self.llm_client.analyze(
                    pdf_text=pdf_text,
                    stock_price=stock_price,
                    currency=currency,
                    symbol=report.symbol,
                    pdf_path=pdf_path,
                    extraction_model=extraction_model,
                    analysis_model=analysis_model,
                    user_profile=user_profile,
                )
            except LLMAnalysisError as e:
                error_str = str(e).lower()
                if "quota" in error_str or "429" in error_str:
                    _logger.warning(
                        f"Multimodal PDF processing failed due to quota/API limits for {report.symbol}. "
                        "Falling back to OCR extractor."
                    )
                    return self._fallback_to_ocr(pdf_path, stock_price, report.symbol, extraction_model, analysis_model, user_profile)
                else:
                    _logger.error(f"Multimodal PDF processing failed for {report.symbol}: {str(e)}")
                    raise
        else:
            currency = self._detect_currency(pdf_text)
            return self.llm_client.analyze(
                pdf_text=pdf_text,
                stock_price=stock_price,
                currency=currency,
                symbol=report.symbol,
                extraction_model=extraction_model,
                analysis_model=analysis_model,
                user_profile=user_profile,
            )
    
    def _fallback_to_ocr(
        self,
        pdf_path: str,
        stock_price: Optional[float],
        symbol: str,
        extraction_model: Optional[str] = "auto",
        analysis_model: Optional[str] = "auto",
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Fallback to OCR extraction when multimodal PDF processing fails.
        
        Args:
            pdf_path: Path to PDF file
            stock_price: Current stock price
            symbol: Stock symbol
            extraction_model: Extraction model preference
            analysis_model: Analysis model preference
            
        Returns:
            Analysis result string
            
        Raises:
            PDFExtractionError: If OCR extraction also fails
        """
        try:
            from financial.pdfplumber_ocr_extractor import PDFPlumberOCRExtractor
            ocr_extractor = PDFPlumberOCRExtractor(use_ocr=True)
            _logger.info(f"Attempting OCR extraction for {symbol}")
            pdf_text = ocr_extractor.extract_text(pdf_path)
            
            if not pdf_text or len(pdf_text.strip()) < 100:
                raise PDFExtractionError(
                    f"OCR extraction also failed for {symbol}. "
                    f"Extracted only {len(pdf_text)} characters."
                )
            
            currency = self._detect_currency(pdf_text)
            _logger.info(f"OCR extraction successful for {symbol}: {len(pdf_text)} characters")
            return self.llm_client.analyze(
                pdf_text=pdf_text,
                stock_price=stock_price,
                currency=currency,
                symbol=symbol,
                extraction_model=extraction_model,
                analysis_model=analysis_model,
                user_profile=user_profile,
            )
        except ImportError:
            raise PDFExtractionError(
                f"OCR libraries not available. Cannot process image-based PDF for {symbol}. "
                "Install with: pip install pdf2image pytesseract"
            )
        except Exception as e:
            raise PDFExtractionError(
                f"OCR extraction failed for {symbol}: {str(e)}"
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


