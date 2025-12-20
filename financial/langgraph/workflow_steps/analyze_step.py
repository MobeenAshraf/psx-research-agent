"""Analyze step for LangGraph workflow."""

import json
import logging
from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig

_logger = logging.getLogger(__name__)


class AnalyzeStep(BaseWorkflowStep):
    """Step 4: Generate investor-focused analysis."""
    
    def __init__(self, state_manager, prompt_manager: PromptManager, llm_helper: LLMHelper):
        super().__init__(state_manager)
        self.prompt_manager = prompt_manager
        self.llm_helper = llm_helper
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute analysis step."""
        try:
            user_profile = state.get("user_profile")
            system_prompt_content = self.prompt_manager.load_system_prompt(user_profile=user_profile)
            analysis_prompt_content = self.prompt_manager.load_analysis_prompt(user_profile=user_profile)
            
            extracted = state.get("extracted_data", {})
            calculated = state.get("calculated_metrics", {})
            
            if not isinstance(extracted, dict):
                extracted = {}
            if not isinstance(calculated, dict):
                calculated = {}
            
            dividend_statements = extracted.get("dividend_statements")
            if not isinstance(dividend_statements, list):
                dividend_statements = []
            
            investor_statements = extracted.get("investor_statements")
            if not isinstance(investor_statements, list):
                investor_statements = []
            
            extracted_json_str = json.dumps(extracted, indent=2)
            calculated_json_str = json.dumps(calculated, indent=2)
            extracted_json_str = extracted_json_str.replace("{", "{{").replace("}", "}}")
            calculated_json_str = calculated_json_str.replace("{", "{{").replace("}", "}}")
            
            statements_context = ""
            if dividend_statements or investor_statements:
                statements_context = "\n\n**CRITICAL: Investor Statements from Extraction:**\n"
                if dividend_statements:
                    statements_context += f"dividend_statements: {json.dumps(dividend_statements, indent=2)}\n"
                if investor_statements:
                    statements_context += f"investor_statements: {json.dumps(investor_statements, indent=2)}\n"
                statements_context += "\n**You MUST incorporate these statements into your analysis.**"
            
            user_prompt_content = f"""{analysis_prompt_content}

Extracted Data:
{extracted_json_str}

Calculated Metrics:
{calculated_json_str}{statements_context}

Provide investor-focused analysis as structured JSON. Return ONLY valid JSON, no additional text."""
            
            user_analysis_model = state.get("analysis_model", "auto")
            analysis_model = ModelConfig.get_analysis_model(user_analysis_model)
            
            _logger.info(f"[ANALYZE STEP] User selected: {user_analysis_model}, Using model: {analysis_model}")
            
            analysis_results, token_usage = self.llm_helper.call_llm_with_json_response(
                system_prompt_content=system_prompt_content,
                user_prompt_content=user_prompt_content,
                model=analysis_model
            )
            
            state["analysis_results"] = analysis_results
            
            if state.get("token_usage") is None:
                state["token_usage"] = {
                    "steps": {},
                    "cumulative": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }
                }
            
            state["token_usage"]["steps"]["analyze"] = token_usage
            
            cumulative = state["token_usage"]["cumulative"]
            cumulative["prompt_tokens"] += token_usage["prompt_tokens"]
            cumulative["completion_tokens"] += token_usage["completion_tokens"]
            cumulative["total_tokens"] += token_usage["total_tokens"]
            
        except Exception as e:
            self._handle_errors(state, e, "analysis_results", {}, "Analysis error: ")
        
        self._save_state(state, "04_analyze")
        return state

