"""Calculate verified financial ratios without relying on model arithmetic."""

from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep
from financial.statement_calculations import calculate_metrics
from financial.statement_values import normalize_statement


class CalculateStep(BaseWorkflowStep):
    def execute(self, state: AnalysisState) -> AnalysisState:
        try:
            extracted = state.get("extracted_data")
            if not isinstance(extracted, dict) or not extracted:
                raise ValueError("No extracted financial statement")
            normalized = normalize_statement(extracted)
            expected_end = state.get("expected_period_end")
            if expected_end and normalized["period_end"] != expected_end:
                raise ValueError(f"Statement period does not match the filing's period end ({expected_end})")
            state["extracted_data"] = normalized
            state["calculated_metrics"] = calculate_metrics(normalized, state.get("stock_price"))
        except Exception as error:
            self._handle_errors(state, error, "calculated_metrics", {}, "Calculation error: ")
        self._save_state(state, "02_calculate")
        return state
