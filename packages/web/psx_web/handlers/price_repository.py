"""Price repository for web package."""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from psx_analysis.models.stock_price import StockPrice


class WebPriceRepository:
    """Price repository for web package that fetches from PSX API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.psx_base_api = "https://dps.psx.com.pk/timeseries/int"
        self.psx_eod_api = "https://dps.psx.com.pk/timeseries/eod"
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price."""
        try:
            url = f"{self.psx_base_api}/{symbol}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not data or 'data' not in data or not data['data']:
                return None
            
            latest = data['data'][-1]
            if len(latest) >= 2:
                return float(latest[1])
            
            return None
        except Exception:
            return None
    
    def get_historical_prices(self, symbol: str, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get historical prices as list of dicts."""
        try:
            days = days or 365
            url = f"{self.psx_eod_api}/{symbol}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not data or 'data' not in data or not data['data']:
                return []
            
            eod_data = data['data']
            if not eod_data:
                return []
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp())
            
            historical_prices = []
            for entry in eod_data:
                if len(entry) < 2:
                    continue
                
                timestamp = entry[0]
                if timestamp < cutoff_timestamp:
                    continue
                
                close_price = float(entry[1])
                volume = float(entry[2]) if len(entry) >= 3 else 0.0
                open_price = float(entry[3]) if len(entry) >= 4 else close_price
                date_obj = datetime.fromtimestamp(timestamp)
                
                high_price = max(open_price, close_price)
                low_price = min(open_price, close_price)
                
                historical_prices.append({
                    'date': date_obj,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            historical_prices.sort(key=lambda x: x['date'])
            return historical_prices
            
        except Exception:
            return []

