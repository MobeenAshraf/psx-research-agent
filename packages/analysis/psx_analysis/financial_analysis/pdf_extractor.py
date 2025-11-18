"""Abstract base class for PDF text extractors."""

from abc import ABC, abstractmethod


class PDFExtractor(ABC):
    """Interface for PDF text extraction."""
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text as string
            
        Raises:
            PDFExtractionError: If extraction fails
        """
        pass

