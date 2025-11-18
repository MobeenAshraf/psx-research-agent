"""File-based implementation of ResultRepository."""

from pathlib import Path
from typing import Optional

from psx_analysis.domain.repositories.result_repository import ResultRepository


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = _find_repo_root()
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "data" / "results"


class FileResultRepository(ResultRepository):
    """Persist analysis results as text files on disk."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_RESULTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_result_path(self, symbol: str, statement_name: str) -> Path:
        symbol_dir = self.base_dir / symbol.upper()
        symbol_dir.mkdir(parents=True, exist_ok=True)
        filename = f"result_{statement_name}.txt"
        return symbol_dir / filename

    def has_result(self, symbol: str, statement_name: str) -> bool:
        return self._get_result_path(symbol, statement_name).exists()

    def get_result(self, symbol: str, statement_name: str) -> Optional[str]:
        result_path = self._get_result_path(symbol, statement_name)
        if not result_path.exists():
            return None
        try:
            return result_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def save_result(self, symbol: str, statement_name: str, content: str) -> None:
        result_path = self._get_result_path(symbol, statement_name)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(content, encoding="utf-8")


