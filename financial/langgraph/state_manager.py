"""State file management for LangGraph workflow."""

import json
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from financial.langgraph.state import AnalysisState


class StateManager:
    """Manages state file saving and directory setup."""
    
    def __init__(self):
        self._state_save_dir: Path = None
        self._current_symbol: str = None
    
    def _generate_model_key(
        self, extraction_model: Optional[str] = None, analysis_model: Optional[str] = None
    ) -> str:
        """Generate model key for directory naming (same logic as FileResultRepository)."""
        extraction = extraction_model or "default"
        analysis = analysis_model or "default"
        
        model_key = f"{extraction}_{analysis}"
        model_key = model_key.replace("/", "_")
        model_key = re.sub(r'[^a-zA-Z0-9_-]', '_', model_key)
        model_key = re.sub(r'_+', '_', model_key)
        model_key = model_key.strip('_')
        
        return model_key
    
    def setup_state_dir(
        self, 
        symbol: str = None, 
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> None:
        """Setup state saving directory."""
        self._current_symbol = symbol
        if symbol:
            base_dir = Path("data/results") / symbol.upper()
            if extraction_model or analysis_model:
                model_key = self._generate_model_key(extraction_model, analysis_model)
                self._state_save_dir = base_dir / model_key / "states"
            else:
                self._state_save_dir = base_dir / "states"
            self._state_save_dir.mkdir(parents=True, exist_ok=True)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._state_save_dir = Path("data/results") / timestamp / "states"
            self._state_save_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, state: AnalysisState, step_name: str) -> None:
        """Save workflow state to JSON file."""
        if not self._state_save_dir:
            return
        
        state_copy = {
            "step": step_name,
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
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_copy, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save state for step {step_name}: {e}", flush=True)

