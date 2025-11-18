"""Custom exceptions for PDF processing operations."""


class PDFDownloadError(Exception):
    """Raised when PDF download fails."""
    pass


class PDFExtractionError(Exception):
    """Raised when PDF text extraction fails."""
    pass


class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""
    pass

