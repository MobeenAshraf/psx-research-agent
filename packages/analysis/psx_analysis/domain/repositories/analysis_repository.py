"""Analysis repository interface."""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from psx_analysis.domain.entities.stock_analysis import StockAnalysis


class AnalysisRepository(ABC):
    """Abstract repository for storing/retrieving stock analyses."""
    
    @abstractmethod
    def save(self, analysis: StockAnalysis) -> None:
        """Save analysis."""
        pass
    
    @abstractmethod
    def get_latest(self, symbol: str) -> Optional[StockAnalysis]:
        """Get latest analysis for symbol."""
        pass
    
    @abstractmethod
    def get_previous_state(self, symbol: str, date: datetime) -> Optional[StockAnalysis]:
        """Get previous analysis state for comparison."""
        pass

