from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StockAnalysis:
    symbol: str
    indicators: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None  # e.g., "buy", "hold", "sell"
    confidence: Optional[float] = None    # 0.0 - 1.0
    reasoning: List[str] = field(default_factory=list)


