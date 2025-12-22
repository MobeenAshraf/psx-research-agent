"""Price repository for web package."""

import requests
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WebPriceRepository:
    """Price repository for web package that fetches from PSX API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.psx_base_api = "https://dps.psx.com.pk/timeseries/int"
        self.psx_eod_api = "https://dps.psx.com.pk/timeseries/eod"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://dps.psx.com.pk/',
            'Origin': 'https://dps.psx.com.pk',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
    
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
            logger.info(f"Fetching historical prices from: {url}")
            
            response = self.session.get(url, timeout=30)
            logger.info(f"PSX API response status: {response.status_code}")
            logger.info(f"PSX API response headers: {dict(response.headers)}")
            if response.status_code == 462:
                logger.error(f"PSX API blocked request (462) for URL: {url}")
                logger.error(f"Response text: {response.text[:500]}")
            response.raise_for_status()
            
            data = response.json()
            if not data or 'data' not in data or not data['data']:
                logger.warning(f"No data in PSX API response for {symbol}")
                return []
            
            eod_data = data['data']
            if not eod_data:
                logger.warning(f"Empty eod_data for {symbol}")
                return []
            
            logger.info(f"Received {len(eod_data)} entries from PSX API for {symbol}")
            
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
            logger.info(f"Returning {len(historical_prices)} historical prices for {symbol}")
            return historical_prices
            
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {type(e).__name__}: {e}")
            return []

