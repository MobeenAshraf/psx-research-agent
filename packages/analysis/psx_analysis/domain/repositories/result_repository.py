"""Abstract repository for result storage."""

from abc import ABC, abstractmethod
from typing import Optional


class ResultRepository(ABC):
    """Interface for result storage operations."""
    
    @abstractmethod
    def has_result(self, symbol: str, statement_name: str) -> bool:
        """Check if result exists for symbol and statement."""
        pass
    
    @abstractmethod
    def get_result(self, symbol: str, statement_name: str) -> Optional[str]:
        """Get cached result if exists."""
        pass
    
    @abstractmethod
    def save_result(self, symbol: str, statement_name: str, content: str) -> None:
        """Save analysis result."""
        pass

