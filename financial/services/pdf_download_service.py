"""Shared PDF download and caching service."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from urllib.parse import urlparse

import requests

from financial.pdf_exceptions import PDFDownloadError
from utils import find_repo_root


PROJECT_ROOT = find_repo_root()
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
        temporary = None
        try:
            if pdf_path.is_file():
                with pdf_path.open("rb") as cached:
                    if cached.read(5) == b"%PDF-":
                        return str(pdf_path)
            with requests.get(url, timeout=(10, 60), stream=True) as response:
                response.raise_for_status()
                with NamedTemporaryFile(dir=pdf_path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    for chunk in response.iter_content(chunk_size=65536):
                        stream.write(chunk)
                    stream.seek(0)
                    if stream.read(5) != b"%PDF-":
                        raise PDFDownloadError("Filing source returned a response other than a PDF")
            temporary.replace(pdf_path)
            return str(pdf_path)
        except requests.RequestException as exc:
            raise PDFDownloadError(f"Failed to download PDF: {exc}") from exc
        except OSError as exc:
            raise PDFDownloadError(f"Error saving PDF: {exc}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _extract_filename(self, url: str, symbol: str) -> str:
        """Generate filename from URL."""
        parsed = Path(urlparse(url).path).name or f"{symbol.upper()}_report.pdf"
        if ".pdf" not in parsed.lower():
            parsed = f"{parsed}.pdf"
        return parsed


