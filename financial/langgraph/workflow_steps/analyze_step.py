"""Analyze step for LangGraph workflow."""

import json
from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.langgraph.prompt_manager import PromptManager
from financial.langgraph.llm_helper import LLMHelper
from financial.config.model_config import ModelConfig


class AnalyzeStep(BaseWorkflowStep):
    """Step 4: Generate investor-focused analysis."""
    
    def __init__(self, state_manager, prompt_manager: PromptManager, llm_helper: LLMHelper):
        super().__init__(state_manager)
        self.prompt_manager = prompt_manager
        self.llm_helper = llm_helper
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute analysis step."""
        try:
            system_prompt_content = self.prompt_manager.load_system_prompt()
            analysis_prompt_content = self.prompt_manager.load_analysis_prompt()
            
            extracted = state.get("extracted_data", {})
            calculated = state.get("calculated_metrics", {})
            
            extracted_json_str = json.dumps(extracted, indent=2)
            calculated_json_str = json.dumps(calculated, indent=2)
            extracted_json_str = extracted_json_str.replace("{", "{{").replace("}", "}}")
            calculated_json_str = calculated_json_str.replace("{", "{{").replace("}", "}}")
            
            user_prompt_content = f"""{analysis_prompt_content}

Extracted Data:
{extracted_json_str}

Calculated Metrics:
{calculated_json_str}

Provide investor-focused analysis as structured JSON. Return ONLY valid JSON, no additional text."""
            
            analysis_results = self.llm_helper.call_llm_with_json_response(
                system_prompt_content=system_prompt_content,
                user_prompt_content=user_prompt_content,
                model=ModelConfig.get_analysis_model()
            )
            
            state["analysis_results"] = analysis_results
            
        except Exception as e:
            self._handle_errors(state, e, "analysis_results", {}, "Analysis error: ")
        
        self._save_state(state, "04_analyze")
        return state

