"""Extract step for LangGraph workflow."""

import logging
from typing import Optional
from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig
from financial.pdf_exceptions import LLMAnalysisError

_logger = logging.getLogger(__name__)


class ExtractStep(BaseWorkflowStep):
    """Step 1: Extract financial data using LLM with structured output."""
    
    def __init__(self, state_manager, prompt_manager: PromptManager, llm_helper: LLMHelper):
        super().__init__(state_manager)
        self.prompt_manager = prompt_manager
        self.llm_helper = llm_helper
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute extraction step."""
        try:
            system_prompt_content = self.prompt_manager.load_system_prompt()
            extraction_prompt_content = self.prompt_manager.load_extraction_prompt()
            
            stock_price_str = ""
            if state.get("stock_price"):
                currency = state.get("currency", "")
                price_str = f"{currency} {state['stock_price']:,.2f}" if currency else f"{state['stock_price']:,.2f}"
                stock_price_str = f"\n\n**Current Stock Price: {price_str}**"
            
            pdf_path = state.get("pdf_path")
            pdf_text = state.get("pdf_text", "")
            
            user_extraction_model = state.get("extraction_model", "auto")
            extraction_model = ModelConfig.get_extraction_model(user_extraction_model)
            is_multimodal = ModelConfig.is_multimodal_model(extraction_model)
            
            _logger.info(f"[EXTRACT STEP] User selected: {user_extraction_model}, Using model: {extraction_model}")
            
            if pdf_path and (is_multimodal or not pdf_text or len(pdf_text.strip()) < 100):
                if is_multimodal:
                    _logger.info(f"User selected multimodal model {extraction_model}, using multimodal PDF extraction")
                else:
                    _logger.info(f"PDF text insufficient, falling back to multimodal PDF extraction")
                
                extracted_data, token_usage = self._extract_with_pdf(
                    pdf_path,
                    system_prompt_content,
                    extraction_prompt_content,
                    stock_price_str,
                    preferred_model=extraction_model if is_multimodal else None
                )
            else:
                _logger.info(f"Using text-based extraction with model: {extraction_model}")
                user_prompt_content = f"""{extraction_prompt_content}{stock_price_str}

{{delimiter}}
EXTRACTED FINANCIAL STATEMENT TEXT (PDF has already been converted to text):
{{delimiter}}

{{pdf_text}}

{{delimiter}}
END OF EXTRACTED TEXT
{{delimiter}}

**YOUR TASK:**
Extract all financial data from the text above and return it as a valid JSON object matching the required schema.

**CRITICAL REQUIREMENTS:**
1. Return ONLY valid JSON - no markdown code blocks, no explanations, no additional text
2. Use numbers (not strings) for all monetary values
3. Use null for missing values (never use 0 or empty string as placeholder)
4. Search ALL sections: Income Statement, Balance Sheet, Cash Flow Statement, Notes
5. Extract exact values as stated in the document - do not estimate or calculate unless explicitly instructed

Return the JSON object now:"""
                
                extracted_data, token_usage = self.llm_helper.call_llm_with_json_response(
                    system_prompt_content=system_prompt_content,
                    user_prompt_content=user_prompt_content,
                    model=extraction_model,
                    state_context={"pdf_text": pdf_text, "delimiter": "="*80}
                )
            
            if not isinstance(extracted_data, dict):
                extracted_data = {}
            
            dividend_statements = extracted_data.get("dividend_statements")
            if not isinstance(dividend_statements, list):
                dividend_statements = []
            extracted_data["dividend_statements"] = dividend_statements
            
            investor_statements = extracted_data.get("investor_statements")
            if not isinstance(investor_statements, list):
                investor_statements = []
            extracted_data["investor_statements"] = investor_statements
            
            state["extracted_data"] = extracted_data
            
            if state.get("token_usage") is None:
                state["token_usage"] = {
                    "steps": {},
                    "cumulative": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }
                }
            
            state["token_usage"]["steps"]["extract"] = token_usage
            
            cumulative = state["token_usage"]["cumulative"]
            cumulative["prompt_tokens"] += token_usage["prompt_tokens"]
            cumulative["completion_tokens"] += token_usage["completion_tokens"]
            cumulative["total_tokens"] += token_usage["total_tokens"]
            
        except Exception as e:
            self._handle_errors(state, e, "extracted_data", {}, "Extraction error: ")
        
        self._save_state(state, "01_extract")
        return state
    
    def _extract_with_pdf(
        self,
        pdf_path: str,
        system_prompt_content: str,
        extraction_prompt_content: str,
        stock_price_str: str,
        preferred_model: Optional[str] = None
    ) -> tuple:
        """
        Extract financial data from PDF using multimodal model.
        
        Args:
            pdf_path: Path to PDF file
            system_prompt_content: System prompt content
            extraction_prompt_content: Extraction prompt content
            stock_price_str: Stock price string to append to prompt
            preferred_model: Preferred model to use (if None, tries all Gemini models)
            
        Returns:
            Tuple of (extracted_data, token_usage)
        """
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
        
        gemini_models = [
            "google/gemini-3-pro-preview",
            "google/gemini-3-flash-preview",
        ]
        
        last_error = None
        for model in gemini_models:
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

