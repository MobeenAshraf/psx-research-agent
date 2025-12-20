"""StockAnalysis domain entity."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StockAnalysis:
    """Comprehensive stock analysis entity."""
    symbol: str
    indicators: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: List[str] = field(default_factory=list)

