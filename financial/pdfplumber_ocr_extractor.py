"""PDF extractor with OCR fallback for image-based PDFs."""

import logging
from pathlib import Path
from typing import Optional, Tuple

import pdfplumber
from financial.pdf_extractor import PDFExtractor
from financial.pdf_exceptions import PDFExtractionError

_logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    _logger.warning(
        "OCR libraries (pdf2image, pytesseract) not available. "
        "Image-based PDFs will not be supported. "
        "Install with: pip install pdf2image pytesseract"
    )


class PDFPlumberOCRExtractor(PDFExtractor):
    """Extract text from PDF using pdfplumber with OCR fallback for image-based PDFs."""
    
    def __init__(self, use_ocr: bool = True, ocr_language: str = "eng"):
        """
        Initialize extractor with OCR support.
        
        Args:
            use_ocr: Whether to use OCR as fallback for image-based PDFs
            ocr_language: Tesseract language code (default: "eng" for English)
        """
        self.use_ocr = use_ocr and OCR_AVAILABLE
        self.ocr_language = ocr_language
        
        if self.use_ocr:
            _logger.info("OCR support enabled for image-based PDFs")
        else:
            if use_ocr and not OCR_AVAILABLE:
                _logger.warning("OCR requested but libraries not available")
    
    def _validate_pdf_file(self, file_path: str) -> None:
        """
        Validate that the file is a valid PDF before attempting extraction.
        
        Args:
            file_path: Path to PDF file
            
        Raises:
            PDFExtractionError: If file is not a valid PDF
        """
        path = Path(file_path)
        
        if not path.exists():
            raise PDFExtractionError(f"PDF file does not exist: {file_path}")
        
        if path.stat().st_size == 0:
            raise PDFExtractionError(f"PDF file is empty: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    raise PDFExtractionError(
                        f"File does not appear to be a valid PDF: {file_path}. "
                        f"Expected PDF header '%PDF', found: {header[:20]}. "
                        "The file may be corrupted or in a different format."
                    )
        except IOError as e:
            raise PDFExtractionError(f"Cannot read PDF file: {file_path}. Error: {str(e)}")
    
    def _extract_with_pdfplumber(self, file_path: str) -> Tuple[str, bool]:
        """
        Extract text using pdfplumber.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, has_content)
        """
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"=== Page {page_num} ===\n{page_text}")
                
                tables = page.extract_tables()
                if tables:
                    for table_num, table in enumerate(tables, 1):
                        if table:
                            table_text = self._format_table(table)
                            if table_text.strip():
                                text_parts.append(
                                    f"=== Page {page_num} - Table {table_num} ===\n{table_text}"
                                )
        
        extracted_text = "\n\n".join(text_parts)
        return extracted_text, len(extracted_text.strip()) > 0
    
    def _extract_with_ocr(self, file_path: str) -> str:
        """
        Extract text from image-based PDF using OCR.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text from all pages
            
        Raises:
            PDFExtractionError: If OCR fails or is not available
        """
        if not self.use_ocr:
            raise PDFExtractionError(
                "OCR is not available. Install pdf2image and pytesseract, "
                "and ensure Tesseract OCR is installed on your system."
            )
        
        try:
            _logger.info(f"Starting OCR extraction for {file_path}")
            images = convert_from_path(file_path, dpi=300)
            _logger.info(f"Converted PDF to {len(images)} images")
            
            text_parts = []
            for page_num, image in enumerate(images, 1):
                _logger.debug(f"Processing page {page_num} with OCR")
                page_text = pytesseract.image_to_string(image, lang=self.ocr_language)
                if page_text.strip():
                    text_parts.append(f"=== Page {page_num} (OCR) ===\n{page_text}")
            
            if not text_parts:
                raise PDFExtractionError(
                    f"OCR extraction returned no text from PDF: {file_path}. "
                    "The images may be too low quality or corrupted."
                )
            
            extracted_text = "\n\n".join(text_parts)
            _logger.info(f"OCR extraction completed: {len(extracted_text)} characters extracted")
            return extracted_text
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            if "TesseractNotFoundError" in error_type or "tesseract" in error_msg.lower():
                raise PDFExtractionError(
                    f"OCR extraction failed: Tesseract OCR is not installed or not in PATH. "
                    f"Install it with: sudo apt-get install tesseract-ocr (Ubuntu/Debian) "
                    f"or brew install tesseract (macOS). "
                    f"See README.md for detailed installation instructions."
                )
            
            raise PDFExtractionError(
                f"OCR extraction failed for PDF: {file_path}. "
                f"Error type: {error_type}, Error: {error_msg}. "
                "Ensure Tesseract OCR is installed and pdf2image dependencies are available."
            )
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text and tables from PDF, with OCR fallback for image-based PDFs.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Combined text from all pages including formatted tables
            
        Raises:
            PDFExtractionError: If extraction fails or file is invalid
        """
        self._validate_pdf_file(file_path)
        
        try:
            extracted_text, has_content = self._extract_with_pdfplumber(file_path)
            
            if has_content:
                _logger.info(f"Successfully extracted text using pdfplumber from {file_path}")
                return extracted_text
            
            if not self.use_ocr:
                raise PDFExtractionError(
                    f"No text or tables found in PDF: {file_path}. "
                    "The PDF may be image-based. Install OCR libraries to process image-based PDFs: "
                    "pip install pdf2image pytesseract"
                )
            
            _logger.info(
                f"No text found with pdfplumber, attempting OCR for {file_path}"
            )
            return self._extract_with_ocr(file_path)
            
        except PDFExtractionError:
            raise
        except pdfplumber.exceptions.PDFSyntaxError as e:
            raise PDFExtractionError(
                f"Invalid or corrupted PDF file: {file_path}. "
                f"PDF syntax error: {str(e)}. "
                "The file may not be a valid PDF or may be corrupted."
            )
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            raise PDFExtractionError(
                f"Failed to extract text from PDF: {file_path}. "
                f"Error type: {error_type}, Error: {error_msg}. "
                "The file may not be a valid PDF or may be in an unsupported format."
            )
    
    def _format_table(self, table: list) -> str:
        """
        Format a table as readable text.
        
        Args:
            table: List of rows, where each row is a list of cells
            
        Returns:
            Formatted table as string
        """
        if not table:
            return ""
        
        formatted_rows = []
        for row in table:
            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
            formatted_rows.append(" | ".join(clean_row))
        
        return "\n".join(formatted_rows)

