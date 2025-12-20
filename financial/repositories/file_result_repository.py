"""File-based implementation of ResultRepository."""

import re
from pathlib import Path
from typing import Optional


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = _find_repo_root()
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "data" / "results"


class FileResultRepository:
    """Persist analysis results as text files on disk."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_RESULTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _generate_model_key(
        self, extraction_model: Optional[str] = None, analysis_model: Optional[str] = None
    ) -> str:
        """
        Generate a sanitized cache key from model combination.
        
        Args:
            extraction_model: Extraction model name
            analysis_model: Analysis model name
            
        Returns:
            Sanitized model key safe for filesystem paths
        """
        extraction = extraction_model or "default"
        analysis = analysis_model or "default"
        
        model_key = f"{extraction}_{analysis}"
        model_key = model_key.replace("/", "_")
        model_key = re.sub(r'[^a-zA-Z0-9_-]', '_', model_key)
        model_key = re.sub(r'_+', '_', model_key)
        model_key = model_key.strip('_')
        
        return model_key

    def _get_result_path(
        self,
        symbol: str,
        statement_name: str,
        extraction_model: Optional[str] = None,
        analysis_model: Optional[str] = None
    ) -> Path:
        symbol_dir = self.base_dir / symbol.upper()
        
        if extraction_model or analysis_model:
            model_key = self._generate_model_key(extraction_model, analysis_model)
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


