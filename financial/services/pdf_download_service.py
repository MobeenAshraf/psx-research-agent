"""Shared PDF download and caching service."""

from pathlib import Path
from typing import Optional

import requests

from financial.pdf_exceptions import PDFDownloadError


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = _find_repo_root()
DEFAULT_PDF_DIR = PROJECT_ROOT / "data" / "financial_statements"


class PDFDownloadService:
    """Download PDF files and cache them on disk."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_PDF_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_pdf_path(self, symbol: str, filename: str) -> Path:
        """Return absolute path for symbol's PDF."""
        symbol_dir = self.base_dir / symbol.upper()
        symbol_dir.mkdir(parents=True, exist_ok=True)
        return symbol_dir / filename

    def download_pdf(self, url: str, symbol: str) -> str:
        """Download PDF if not cached and return file path."""
        filename = self._extract_filename(url, symbol)
        pdf_path = self.get_pdf_path(symbol, filename)
        if pdf_path.exists():
            return str(pdf_path)

        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            with open(pdf_path, "wb") as file_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    file_obj.write(chunk)
            return str(pdf_path)
        except requests.RequestException as exc:
            raise PDFDownloadError(f"Failed to download PDF: {exc}") from exc
        except OSError as exc:
            raise PDFDownloadError(f"Error saving PDF: {exc}") from exc

    def _extract_filename(self, url: str, symbol: str) -> str:
        """Generate filename from URL."""
        parsed = url.split("/")[-1] or f"{symbol.upper()}_report.pdf"
        if ".pdf" not in parsed.lower():
            parsed = f"{parsed}.pdf"
        return parsed


