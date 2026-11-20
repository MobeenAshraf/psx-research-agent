"""State file management for LangGraph workflow."""

import json
from typing import Optional
from pathlib import Path
from financial.result_paths import DEFAULT_RESULTS_DIRECTORY, model_directory
from datetime import datetime
from tempfile import NamedTemporaryFile
from uuid import uuid4
from financial.langgraph.state import AnalysisState


class StateManager:
    """Manages state file saving and directory setup."""
    
    def __init__(self):
        self._state_save_dir: Path = None
        self._run_id: Optional[str] = None

    @property
    def run_started(self) -> bool:
        return self._run_id is not None
    
    def setup_state_dir(
        self, 
        symbol: str = None, 
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> None:
        """Setup state saving directory."""
        self._run_id = uuid4().hex
        if symbol:
            base_dir = DEFAULT_RESULTS_DIRECTORY / symbol.upper()
            if extraction_model or analysis_model:
                model_key = model_directory(extraction_model, analysis_model)
                self._state_save_dir = base_dir / model_key / "states"
            else:
                self._state_save_dir = base_dir / "states"
            self._state_save_dir.mkdir(parents=True, exist_ok=True)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._state_save_dir = DEFAULT_RESULTS_DIRECTORY / timestamp / "states"
            self._state_save_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, state: AnalysisState, step_name: str) -> None:
        """Save workflow state to JSON file."""
        if not self._state_save_dir:
            return
        
        state_copy = {
            "step": step_name,
            "run_id": self._run_id,
            "report_url": state.get("report_url"),
            "timestamp": datetime.now().isoformat(),
            "stock_price": state.get("stock_price"),
            "currency": state.get("currency"),
            "extracted_data": state.get("extracted_data"),
            "calculated_metrics": state.get("calculated_metrics"),
            "validation_results": state.get("validation_results"),
            "analysis_results": state.get("analysis_results"),
            "final_report": state.get("final_report"),
            "errors": state.get("errors", []),
            "token_usage": state.get("token_usage"),
        }
        
        if "pdf_text" in state:
            pdf_text = state["pdf_text"]
            state_copy["pdf_text_length"] = len(pdf_text) if pdf_text else 0
            state_copy["pdf_text_preview"] = pdf_text[:500] if pdf_text else ""
        
        state_file = self._state_save_dir / f"{step_name}_state.json"
        temporary = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._state_save_dir, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(state_copy, stream, indent=2, ensure_ascii=False)
            temporary.replace(state_file)
        except OSError as error:
            print(f"Warning: Failed to save state for step {step_name}: {error}", flush=True)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
