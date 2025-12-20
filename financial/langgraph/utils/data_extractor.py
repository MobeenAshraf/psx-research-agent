"""Data extraction utilities for financial data."""

from typing import Any, Dict, Optional


class DataExtractor:
    """Utility class for extracting data from financial statements."""
    
    @staticmethod
    def get_revenue(data: Dict[str, Any]) -> Optional[float]:
        """Extract revenue value handling dict format."""
        revenue_data = data.get("revenue")
        if isinstance(revenue_data, dict):
            return revenue_data.get("current")
        return revenue_data

