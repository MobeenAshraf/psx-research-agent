"""Base class for workflow steps with shared error handling."""

from abc import ABC, abstractmethod
from typing import Any
from psx_analysis.financial_analysis.langgraph.state import AnalysisState
from psx_analysis.financial_analysis.langgraph.state_manager import StateManager


class BaseWorkflowStep(ABC):
    """Base class for workflow steps with shared error handling and state management."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    @abstractmethod
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute the workflow step."""
        pass
    
    def _handle_errors(
        self,
        state: AnalysisState,
        error: Exception,
        step_name: str,
        default_value: Any,
        error_prefix: str = ""
    ) -> None:
        """Handle errors and update state."""
        import traceback
        error_msg = f"{error_prefix}{type(error).__name__}: {str(error)}"
        error_msg += f"\nTraceback: {traceback.format_exc()}"
        state["errors"].append(error_msg)
        if isinstance(default_value, dict):
            state[step_name] = {}
        else:
            state[step_name] = default_value
    
    def _save_state(self, state: AnalysisState, step_name: str) -> None:
        """Save state after step execution."""
        self.state_manager.save_state(state, step_name)

