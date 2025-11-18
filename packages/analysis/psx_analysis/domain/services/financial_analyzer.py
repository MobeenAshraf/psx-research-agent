"""Financial analysis domain service."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class FinancialAnalyzer(ABC):
    """Abstract financial analysis service."""
    
    @abstractmethod
    def analyze_report(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Analyze latest financial report for symbol."""
        pass
    
    @abstractmethod
    def extract_metrics(self, report_data: Any) -> Dict[str, Any]:
        """Extract key financial metrics from report."""
        pass

