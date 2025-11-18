"""StockAnalysis domain entity."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class StockAnalysis:
    """Comprehensive stock analysis entity."""
    symbol: str
    indicators: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None  # 'buy', 'hold', 'sell'
    confidence: Optional[float] = None    # 0.0 - 1.0
    reasoning: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    def is_buy_signal(self) -> bool:
        """Check if analysis indicates buy signal."""
        return self.recommendation == 'Buy' and self.confidence and self.confidence >= 0.5
    
    def is_sell_signal(self) -> bool:
        """Check if analysis indicates sell signal."""
        return self.recommendation == 'Sell' and self.confidence and self.confidence >= 0.5

