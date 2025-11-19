"""Main LangGraph analyzer orchestrator."""

from typing import Optional
from langgraph.graph import StateGraph, END
from financial.pdf_exceptions import LLMAnalysisError
from financial.langgraph.state import AnalysisState
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.json_parser import JSONParser
from financial.langgraph.api_client import OpenRouterAPIClient
from financial.langgraph.llm_helper import LLMHelper
from financial.langgraph.state_manager import StateManager
from financial.langgraph.workflow_steps.extract_step import ExtractStep
from financial.langgraph.workflow_steps.calculate_step import CalculateStep
from financial.langgraph.workflow_steps.validate_step import ValidateStep
from financial.langgraph.workflow_steps.analyze_step import AnalyzeStep
from financial.langgraph.workflow_steps.format_step import FormatStep
from financial.financial_metrics_validator import FinancialMetricsValidator
import os


class LangGraphAnalyzer:
    """Multi-step financial analysis using LangGraph."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        
        # Initialize components
        self.prompt_manager = PromptManager()
        self.json_parser = JSONParser()
        self.api_client = OpenRouterAPIClient(self.api_key)
        self.llm_helper = LLMHelper(self.api_client, self.json_parser)
        self.state_manager = StateManager()
        self.validator = FinancialMetricsValidator()
        
        # Initialize workflow steps
        self.extract_step = ExtractStep(self.state_manager, self.prompt_manager, self.llm_helper)
        self.calculate_step = CalculateStep(self.state_manager)
        self.validate_step = ValidateStep(self.state_manager, self.validator)
        self.analyze_step = AnalyzeStep(self.state_manager, self.prompt_manager, self.llm_helper)
        self.format_step = FormatStep(self.state_manager)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AnalysisState)
        
        workflow.add_node("extract", self.extract_step.execute)
        workflow.add_node("calculate", self.calculate_step.execute)
        workflow.add_node("validate", self.validate_step.execute)
        workflow.add_node("analyze", self.analyze_step.execute)
        workflow.add_node("format", self.format_step.execute)
        
        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "calculate")
        workflow.add_edge("calculate", "validate")
        workflow.add_edge("validate", "analyze")
        workflow.add_edge("analyze", "format")
        workflow.add_edge("format", END)
        
        return workflow.compile()
    
    def analyze(
        self,
        pdf_text: str,
        stock_price: Optional[float] = None,
        currency: str = "",
        symbol: Optional[str] = None
    ) -> str:
        """
        Run the complete analysis workflow.
        
        Args:
            pdf_text: Extracted PDF text content
            stock_price: Current stock price (optional)
            currency: Currency symbol (optional)
            symbol: Stock symbol (optional, used for state saving)
            
        Returns:
            Final formatted report as string
        """
        if not pdf_text or not pdf_text.strip():
            raise LLMAnalysisError("No PDF text content provided for analysis")
        
        self.state_manager.setup_state_dir(symbol)
        
        initial_state: AnalysisState = {
            "pdf_text": pdf_text,
            "stock_price": stock_price,
            "currency": currency,
            "extracted_data": None,
            "calculated_metrics": None,
            "validation_results": None,
            "analysis_results": None,
            "final_report": None,
            "errors": [],
            "token_usage": {
                "steps": {},
                "cumulative": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            },
        }
        
        self.state_manager.save_state(initial_state, "00_initial")
        
        result = self.workflow.invoke(initial_state)
        
        self.state_manager.save_state(result, "99_final")
        
        if result.get("errors"):
            error_msg = "; ".join(result["errors"])
            raise LLMAnalysisError(f"Analysis errors: {error_msg}")
        
        return result.get("final_report", "Analysis completed but no report generated.")

