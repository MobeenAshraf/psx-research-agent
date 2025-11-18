from abc import ABC, abstractmethod
from typing import Dict, List, Any


class TechnicalAnalyzer(ABC):
    """Abstract technical analysis service."""
    
    @abstractmethod
    def calculate_indicators(self, price_data: List[Dict]) -> Dict[str, Any]:
        """Calculate technical indicators from price data."""
        pass
    
    @abstractmethod
    def generate_signals(self, indicators: Dict[str, Any]) -> List[str]:
        """Generate trading signals from indicators."""
        pass
    
    @abstractmethod
    def identify_support_resistance(self, price_data: List[Dict]) -> Dict[str, float]:
        """Identify support and resistance levels."""
        pass

