from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class PriceRepository(ABC):
    """Abstract repository for price data access."""
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        pass
    
    @abstractmethod
    def get_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols."""
        pass
    
    @abstractmethod
    def get_historical_prices(
        self, 
        symbol: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None
    ) -> List[Dict]:
        """Get historical price data."""
        pass

