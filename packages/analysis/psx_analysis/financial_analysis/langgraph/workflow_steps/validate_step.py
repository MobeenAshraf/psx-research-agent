"""Validate step for LangGraph workflow."""

from psx_analysis.financial_analysis.langgraph.state import AnalysisState
from psx_analysis.financial_analysis.langgraph.workflow_steps.base_step import BaseWorkflowStep
from psx_analysis.financial_analysis.financial_metrics_validator import FinancialMetricsValidator


class ValidateStep(BaseWorkflowStep):
    """Step 3: Validate extracted data and cross-check consistency."""
    
    def __init__(self, state_manager, validator: FinancialMetricsValidator):
        super().__init__(state_manager)
        self.validator = validator
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute validation step."""
        try:
            extracted = state.get("extracted_data")
            calculated = state.get("calculated_metrics") or {}
            
            if extracted is None or not isinstance(extracted, dict):
                state["errors"].append("Cannot validate: extraction data is None or invalid")
                state["validation_results"] = {"is_valid": False, "errors": ["No data to validate"], "warnings": []}
                return state
            
            validation_data = {**extracted, **calculated}
            validation_results = self.validator.validate_all(validation_data)
            state["validation_results"] = validation_results
            
        except Exception as e:
            self._handle_errors(state, e, "validation_results", {"is_valid": False, "errors": [str(e)], "warnings": []}, "Validation error: ")
        
        self._save_state(state, "03_validate")
        return state

