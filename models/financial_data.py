from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from .base import SerializableDataclass, parse_datetime


@dataclass
class FinancialData(SerializableDataclass):
    symbol: str
    report_type: str
    period_ended: str
    posting_date: datetime
    book_value: Optional[float] = None
    price_to_book: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_policy_changed: bool = False
    new_investments: Optional[str] = None
    major_losses: Optional[str] = None
    report_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialData':
        posting_date = parse_datetime(data.get('posting_date'))
        return cls(
            symbol=data['symbol'],
            report_type=data['report_type'],
            period_ended=data['period_ended'],
            posting_date=posting_date,
            book_value=float(data['book_value']) if data.get('book_value') else None,
            price_to_book=float(data['price_to_book']) if data.get('price_to_book') else None,
            eps=float(data['eps']) if data.get('eps') else None,
            dividend_yield=float(data['dividend_yield']) if data.get('dividend_yield') else None,
            dividend_policy_changed=bool(data.get('dividend_policy_changed', False)),
            new_investments=data.get('new_investments'),
            major_losses=data.get('major_losses'),
            report_url=data.get('report_url')
        )

