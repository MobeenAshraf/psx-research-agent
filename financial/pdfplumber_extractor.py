"""PDFPlumber-based PDF text extractor."""

import pdfplumber
from financial.pdf_extractor import PDFExtractor
from financial.pdf_exceptions import PDFExtractionError


class PDFPlumberExtractor(PDFExtractor):
    """Extract text from PDF using pdfplumber."""
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text and tables from PDF.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Combined text from all pages including formatted tables
        """
        try:
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract regular text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"=== Page {page_num} ===\n{page_text}")
                    
                    # Extract tables (important for financial statements)
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            if table:
                                # Format table as readable text
                                table_text = self._format_table(table)
                                if table_text.strip():
                                    text_parts.append(
                                        f"=== Page {page_num} - Table {table_num} ===\n{table_text}"
                                    )
            
            if not text_parts:
                raise PDFExtractionError(
                    f"No text or tables found in PDF: {file_path}. "
                    "The PDF may be image-based or corrupted."
                )
            
            return "\n\n".join(text_parts)
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")
    
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
            # Filter out None values and convert to strings
            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
            # Join cells with pipe separator for readability
            formatted_rows.append(" | ".join(clean_row))
        
        return "\n".join(formatted_rows)

