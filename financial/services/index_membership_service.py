"""Index membership service for fetching stock index and ETF weightages."""

from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from technical.price_repository import WebPriceRepository

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
KSE100_URL = "https://dps.psx.com.pk/indices/KSE100"
KMI30_URL = "https://dps.psx.com.pk/indices/KMI30"
MZNETF_URL = "https://dps.psx.com.pk/etf/MZNPETF"


class IndexMembershipService:
    """Service for fetching and caching index membership and weightage data."""

    def __init__(self):
        self.kse100: Dict[str, float] = {}
        self.kmi30: Dict[str, float] = {}
        self.mznetf: Dict[str, float] = {}
        self._initialized = False
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _load_all_indices(self) -> None:
        """Load all index data into memory dictionaries."""
        if self._initialized:
            return

        self._load_kse100()
        self._load_kmi30()
        self._load_mznetf()
        self._initialized = True

    def _load_kse100(self) -> None:
        """Load KSE100 index data."""
        try:
            response = self.session.get(KSE100_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table")
            if not table:
                return

            rows = table.find_all("tr")[1:]
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                symbol_cell = cells[0]
                symbol_link = symbol_cell.find("a")
                if symbol_link:
                    symbol = symbol_link.text.strip().upper()
                else:
                    symbol = symbol_cell.text.strip().upper()

                weightage_cell = cells[6]
                weightage_str = weightage_cell.text.strip()

                if symbol and weightage_str:
                    try:
                        weightage = float(weightage_str.replace("%", ""))
                        self.kse100[symbol] = weightage
                    except (ValueError, AttributeError):
                        continue
        except Exception:
            pass

    def _load_kmi30(self) -> None:
        """Load KMI30 index data."""
        try:
            response = self.session.get(KMI30_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table")
            if not table:
                return

            rows = table.find_all("tr")[1:]
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                symbol_cell = cells[0]
                symbol_link = symbol_cell.find("a")
                if symbol_link:
                    symbol = symbol_link.text.strip().upper()
                else:
                    symbol = symbol_cell.text.strip().upper()

                weightage_cell = cells[6]
                weightage_str = weightage_cell.text.strip()

                if symbol and weightage_str:
                    try:
                        weightage = float(weightage_str.replace("%", ""))
                        self.kmi30[symbol] = weightage
                    except (ValueError, AttributeError):
                        continue
        except Exception:
            pass

    def _load_mznetf(self) -> None:
        """Load MZNETF ETF underlying basket holdings from the ETF page."""
        try:
            response = self.session.get(MZNETF_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            modal = soup.find("div", class_="etfCub__modal")
            if not modal:
                return

            table = modal.find("table")
            if not table:
                return

            rows = table.find_all("tr")[1:]
            total_value = 0.0
            holdings = []

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                symbol_cell = cells[0]
                symbol_link = symbol_cell.find("a")
                if symbol_link:
                    symbol = symbol_link.find("strong")
                    symbol = symbol.text.strip().upper() if symbol else symbol_link.text.strip().upper()
                else:
                    symbol = symbol_cell.text.strip().upper()

                shares_str = cells[2].text.strip().replace(",", "")
                try:
                    shares = float(shares_str)
                    holdings.append({"symbol": symbol, "shares": shares})
                except ValueError:
                    continue

            if not holdings:
                return

            try:
                price_repo = WebPriceRepository()
                
                for holding in holdings:
                    symbol = holding["symbol"]
                    shares = holding["shares"]
                    current_price = price_repo.get_current_price(symbol)
                    if current_price:
                        value = shares * current_price
                        holding["value"] = value
                        total_value += value
                    else:
                        holding["value"] = 0.0

                if total_value > 0:
                    for holding in holdings:
                        if holding.get("value", 0) > 0:
                            weightage = (holding["value"] / total_value) * 100
                            self.mznetf[holding["symbol"]] = round(weightage, 2)
            except Exception:
                pass
        except Exception:
            pass

    def get_index_membership(self, symbol: str) -> Dict[str, Any]:
        """
        Get index membership and weightage for a symbol.

        Args:
            symbol: Stock symbol (case-insensitive)

        Returns:
            Dictionary with index membership data:
            {
                "kse100": {"included": bool, "weightage": float or None},
                "kmi30": {"included": bool, "weightage": float or None},
                "mznetf": {"included": bool, "weightage": float or None}
            }
        """
        if not self._initialized:
            self._load_all_indices()

        symbol_upper = symbol.upper()

        kse100_weightage = self.kse100.get(symbol_upper)
        kmi30_weightage = self.kmi30.get(symbol_upper)
        mznetf_weightage = self.mznetf.get(symbol_upper)

        return {
            "kse100": {
                "included": kse100_weightage is not None,
                "weightage": kse100_weightage
            },
            "kmi30": {
                "included": kmi30_weightage is not None,
                "weightage": kmi30_weightage
            },
            "mznetf": {
                "included": mznetf_weightage is not None,
                "weightage": mznetf_weightage
            }
        }


_shared_instance: Optional[IndexMembershipService] = None


def get_index_service() -> IndexMembershipService:
    """
    Get the shared singleton instance of IndexMembershipService.
    This ensures data is loaded once and reused across all API calls.
    """
    global _shared_instance
    if _shared_instance is None:
        _shared_instance = IndexMembershipService()
    return _shared_instance

