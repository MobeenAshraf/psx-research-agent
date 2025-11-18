"""Extract step for LangGraph workflow."""

from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig


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
            
            extracted_data = self.llm_helper.call_llm_with_json_response(
                system_prompt_content=system_prompt_content,
                user_prompt_content=user_prompt_content,
                model=ModelConfig.get_extraction_model(),
                state_context={"pdf_text": state["pdf_text"], "delimiter": "="*80}
            )
            
            state["extracted_data"] = extracted_data
            
        except Exception as e:
            self._handle_errors(state, e, "extracted_data", {}, "Extraction error: ")
        
        self._save_state(state, "01_extract")
        return state

