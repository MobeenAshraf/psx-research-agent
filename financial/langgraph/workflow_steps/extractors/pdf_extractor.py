"""PDF extraction utilities for multimodal processing."""

import logging
from typing import Optional, Tuple, Dict, Any
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig
from financial.pdf_exceptions import LLMAnalysisError

_logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract financial data from PDF using multimodal models."""
    
    def __init__(self, llm_helper: LLMHelper):
        self.llm_helper = llm_helper
    
    def extract_with_pdf(
        self,
        pdf_path: str,
        system_prompt_content: str,
        extraction_prompt_content: str,
        stock_price_str: str,
        preferred_model: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Extract financial data from PDF using multimodal model."""
        user_prompt_content = f"""{extraction_prompt_content}{stock_price_str}

**YOUR TASK:**
Extract all financial data from the PDF document and return it as a valid JSON object matching the required schema.

**CRITICAL REQUIREMENTS:**
1. Return ONLY valid JSON - no markdown code blocks, no explanations, no additional text
2. Use numbers (not strings) for all monetary values
3. Use null for missing values (never use 0 or empty string as placeholder)
4. Search ALL sections: Income Statement, Balance Sheet, Cash Flow Statement, Notes
5. Extract exact values as stated in the document - do not estimate or calculate unless explicitly instructed
6. Read the PDF carefully - look for tables, financial statements, and numerical data

Return the JSON object now:"""
        
        if preferred_model and ModelConfig.is_multimodal_model(preferred_model):
            try:
                _logger.info(f"Using user-selected Gemini model: {preferred_model}")
                extracted_data, token_usage = self.llm_helper.call_llm_with_pdf(
                    pdf_path=pdf_path,
                    system_prompt_content=system_prompt_content,
                    user_prompt_content=user_prompt_content,
                    model=preferred_model,
                    state_context={}
                )
                return extracted_data, token_usage
            except LLMAnalysisError as e:
                _logger.warning(f"User-selected model {preferred_model} failed: {str(e)}")
        
        last_error = None
        for model in ModelConfig.GEMINI_MODELS:
            try:
                _logger.info(f"Attempting PDF extraction with model: {model}")
                extracted_data, token_usage = self.llm_helper.call_llm_with_pdf(
                    pdf_path=pdf_path,
                    system_prompt_content=system_prompt_content,
                    user_prompt_content=user_prompt_content,
                    model=model,
                    state_context={}
                )
                _logger.info(f"Successfully extracted data using model: {model}")
                return extracted_data, token_usage
            except LLMAnalysisError as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    _logger.warning(f"Quota exceeded for {model}, trying next model...")
                    last_error = e
                    continue
                else:
                    _logger.error(f"Error with {model}: {str(e)}")
                    last_error = e
                    continue
        
        if last_error:
            raise LLMAnalysisError(
                f"All Gemini models failed for PDF extraction. Last error: {str(last_error)}"
            )
        raise LLMAnalysisError("No Gemini models available for PDF extraction")

