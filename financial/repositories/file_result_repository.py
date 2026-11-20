"""File-based implementation of ResultRepository."""

import json
from pathlib import Path
from typing import Optional
from utils import find_repo_root
from financial.result_paths import DEFAULT_RESULTS_DIRECTORY, model_directory


PROJECT_ROOT = find_repo_root()
DEFAULT_RESULTS_DIR = PROJECT_ROOT / DEFAULT_RESULTS_DIRECTORY


class FileResultRepository:
    """Persist analysis results as text files on disk."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_RESULTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_result_path(
        self,
        symbol: str,
        statement_name: str,
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> Path:
        symbol_dir = self.base_dir / symbol.upper()
        
        if extraction_model or analysis_model:
            model_key = model_directory(extraction_model, analysis_model)
            symbol_dir = symbol_dir / model_key
        
        symbol_dir.mkdir(parents=True, exist_ok=True)
        filename = f"result_{statement_name}.txt"
        return symbol_dir / filename

    def has_result(
        self,
        symbol: str,
        statement_name: str,
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> bool:
        return self._get_result_path(symbol, statement_name, extraction_model, analysis_model).exists()

    def has_valid_analysis(
        self, symbol, statement_name, report_url, extraction_model=None, analysis_model=None
    ) -> bool:
        result_path = self._get_result_path(symbol, statement_name, extraction_model, analysis_model)
        if not result_path.is_file():
            return False
        states = result_path.parent / "states"
        try:
            initial = json.loads((states / "00_initial_state.json").read_text(encoding="utf-8"))
            final = json.loads((states / "99_final_state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return (
            initial.get("run_id") is not None
            and initial["run_id"] == final.get("run_id")
            and final.get("report_url") == report_url
            and not final.get("errors")
            and (final.get("validation_results") or {}).get("is_valid") is True
        )

    def get_result(
        self,
        symbol: str,
        statement_name: str,
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> Optional[str]:
        result_path = self._get_result_path(symbol, statement_name, extraction_model, analysis_model)
        if not result_path.exists():
            return None
        try:
            return result_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def save_result(
        self,
        symbol: str,
        statement_name: str,
        content: str,
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> None:
        result_path = self._get_result_path(symbol, statement_name, extraction_model, analysis_model)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(content, encoding="utf-8")


