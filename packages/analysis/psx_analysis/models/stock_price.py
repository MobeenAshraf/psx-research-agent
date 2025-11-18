from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from .base import SerializableDataclass, parse_datetime


@dataclass
class StockPrice(SerializableDataclass):
    symbol: str
    price: float
    volume: float
    date: datetime
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockPrice':
        date = parse_datetime(data.get('date'))
        return cls(
            symbol=data['symbol'],
            price=float(data['price']),
            volume=float(data.get('volume', 0)),
            date=date,
            high=float(data['high']) if data.get('high') else None,
            low=float(data['low']) if data.get('low') else None,
            open=float(data['open']) if data.get('open') else None,
            close=float(data['close']) if data.get('close') else None
        )

