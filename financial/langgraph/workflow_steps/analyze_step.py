"""Analyze step for LangGraph workflow."""

import logging
from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig
from financial.prompt_builders import build_analysis_prompt

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
            
            user_prompt_content = build_analysis_prompt(analysis_prompt_content, state)

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
            
            token_usage_with_model = dict(token_usage)
            token_usage_with_model["model"] = analysis_model
            state["token_usage"]["steps"]["analyze"] = token_usage_with_model
            
            cumulative = state["token_usage"]["cumulative"]
            cumulative["prompt_tokens"] += token_usage["prompt_tokens"]
            cumulative["completion_tokens"] += token_usage["completion_tokens"]
            cumulative["total_tokens"] += token_usage["total_tokens"]
            
        except Exception as e:
            self._handle_errors(state, e, "analysis_results", {}, "Analysis error: ")
        
        self._save_state(state, "04_analyze")
        return state
