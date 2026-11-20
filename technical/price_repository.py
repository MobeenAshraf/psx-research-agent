"""Load daily prices from PSX with a split-adjusted close fallback."""

import csv
from datetime import datetime, timedelta
import io
import logging
from math import isfinite
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests


logger = logging.getLogger(__name__)
MARKET_TZ = ZoneInfo("Asia/Karachi")
MAX_PRICE_AGE_DAYS = 7


class WebPriceRepository:
    def __init__(self):
        self.session = requests.Session()
        self.psx_base_api = "https://dps.psx.com.pk/timeseries/int"
        self.psx_eod_api = "https://dps.psx.com.pk/timeseries/eod"
        self.superx_history_api = "https://superx.pk/chart"

    def get_current_price(self, symbol: str, *, daily_fallback: bool = True) -> Optional[float]:
        """Return a recent intraday quote or the last available daily close."""
        symbol = quote(symbol.strip().upper(), safe="")
        now = datetime.now(MARKET_TZ)
        try:
            response = self.session.get(f"{self.psx_base_api}/{symbol}", timeout=8)
            response.raise_for_status()
            quotes = [
                (self._psx_date(row[0]), self._number(row[1]))
                for row in response.json().get("data", []) or []
                if isinstance(row, (list, tuple)) and len(row) >= 2
            ]
            recent = [
                (timestamp, price) for timestamp, price in quotes
                if timestamp is not None and now - timedelta(days=MAX_PRICE_AGE_DAYS) <= timestamp <= now
                and price is not None and price > 0
            ]
            if recent:
                return max(recent)[1]
        except (requests.RequestException, AttributeError, TypeError, ValueError) as error:
            logger.info("PSX quote unavailable for %s: %s", symbol, error)

        if not daily_fallback:
            return None
        history = self._fetch_history(symbol, now, MAX_PRICE_AGE_DAYS, min_sessions=1)
        return history[-1]["close"] if history else None

    def get_historical_prices(self, symbol: str, days: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._fetch_history(
            quote(symbol.strip().upper(), safe=""), datetime.now(MARKET_TZ), days or 365, min_sessions=50
        )

    def _fetch_history(self, symbol, now, days, min_sessions):
        cutoff = now.date() - timedelta(days=days)
        psx = self._fetch_psx_history(symbol, cutoff, now.date())
        recent_cutoff = now.date() - timedelta(days=MAX_PRICE_AGE_DAYS)
        if len(psx) >= min_sessions and psx[-1]["date"].date() >= recent_cutoff:
            return psx

        fallback = self._fetch_superx_history(symbol, cutoff, now.date())
        if fallback and (
            not psx
            or (len(fallback) >= min_sessions and len(psx) < min_sessions)
            or (
                len(fallback) >= min_sessions
                and psx[-1]["date"].date() < recent_cutoff
                and fallback[-1]["date"] > psx[-1]["date"]
            )
        ):
            return fallback
        return psx

    def _fetch_psx_history(self, symbol, cutoff, today):
        history = {}
        try:
            response = self.session.get(f"{self.psx_eod_api}/{symbol}", timeout=8)
            response.raise_for_status()
            for row in response.json().get("data", []) or []:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                timestamp = self._psx_date(row[0])
                close = self._number(row[1])
                if timestamp is None or not cutoff <= timestamp.date() <= today or close is None or close <= 0:
                    continue
                session = timestamp.date()
                if session in history and timestamp <= history[session]["date"]:
                    continue
                history[session] = {
                    "date": timestamp,
                    "open": self._number(row[3], minimum=0) if len(row) > 3 else None,
                    "close": close,
                    "volume": self._number(row[2], minimum=0) if len(row) > 2 else None,
                    "source": "PSX",
                    "adjustment": "unverified",
                }
        except (requests.RequestException, AttributeError, TypeError, ValueError) as error:
            logger.warning("PSX daily history unavailable for %s: %s", symbol, error)
        return [history[session] for session in sorted(history)]

    def _fetch_superx_history(self, symbol, cutoff, today):
        history = {}
        try:
            response = self.session.get(f"{self.superx_history_api}/{symbol}.csv", timeout=8)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text.lstrip("\ufeff")))
            if not {"date", "close_adjusted", "volume"}.issubset(reader.fieldnames or []):
                logger.warning("Unexpected SuperX CSV for %s", symbol)
                return []
            for row in reader:
                try:
                    timestamp = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=MARKET_TZ)
                except (TypeError, ValueError):
                    continue
                close = self._number(row["close_adjusted"])
                if not cutoff <= timestamp.date() <= today or close is None or close <= 0:
                    continue
                # The CSV guarantees the close adjustment basis only.
                history[timestamp.date()] = {
                    "date": timestamp,
                    "close": close,
                    "volume": self._number(row["volume"], minimum=0),
                    "source": "SuperX (PSX daily data)",
                    "adjustment": "splits and bonus issues",
                }
        except (requests.RequestException, csv.Error) as error:
            logger.warning("SuperX daily history unavailable for %s: %s", symbol, error)
        return [history[session] for session in sorted(history)]

    @staticmethod
    def _number(value, minimum=None):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if isfinite(number) and (minimum is None or number >= minimum):
            return number
        return None

    @classmethod
    def _psx_date(cls, value):
        number = cls._number(value)
        if number is None:
            return None
        try:
            return datetime.fromtimestamp(number, MARKET_TZ)
        except (ValueError, OverflowError, OSError):
            return None
