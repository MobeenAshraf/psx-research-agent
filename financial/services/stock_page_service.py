"""Stock page service for fetching financial data from PSX company pages."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_COMPANY_URL = "https://dps.psx.com.pk/company"


@dataclass
class StockPageFinancials:
    """Financial data extracted from PSX stock page."""

    symbol: str
    annual_data: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    quarterly_data: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    ratios: Dict[str, Dict[str, Optional[float]]] = field(default_factory=dict)
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


class StockPageService:
    """Fetch and parse financial data from PSX stock pages with validation."""

    MINIMUM_ANNUAL_YEARS = 2
    MINIMUM_QUARTERLY_PERIODS = 2
    MINIMUM_METRICS_PER_PERIOD = 2

    def __init__(self, base_url: str = BASE_COMPANY_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_stock_financials(self, symbol: str) -> Optional[StockPageFinancials]:
        """Fetch and validate financial data from PSX stock page.

        Returns StockPageFinancials if data is valid and reliable, None otherwise.
        """
        symbol_upper = symbol.upper()
        result = StockPageFinancials(symbol=symbol_upper)

        try:
            html_content = self._fetch_page(symbol_upper)
            if not html_content:
                _logger.warning(f"Failed to fetch page for {symbol_upper}")
                return None

            soup = BeautifulSoup(html_content, "html.parser")

            if not self._verify_page_structure(soup, result):
                _logger.warning(
                    f"Page structure verification failed for {symbol_upper}: "
                    f"{result.validation_errors}"
                )
                return None

            self._extract_annual_financials(soup, result)
            self._extract_quarterly_financials(soup, result)
            self._extract_ratios(soup, result)

            if not self._validate_data(result):
                _logger.warning(
                    f"Data validation failed for {symbol_upper}: "
                    f"{result.validation_errors}"
                )
                return None

            result.is_valid = True
            return result

        except Exception as exc:
            _logger.error(f"Error fetching stock page data for {symbol_upper}: {exc}")
            return None

    def _fetch_page(self, symbol: str) -> Optional[str]:
        """Fetch the stock page HTML content."""
        url = f"{self.base_url}/{symbol}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                _logger.warning(f"Stock page not found for {symbol}")
                return None
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            _logger.error(f"Network error fetching {symbol}: {exc}")
            return None

    def _verify_page_structure(
        self, soup: BeautifulSoup, result: StockPageFinancials
    ) -> bool:
        """Verify page contains expected data structure."""
        has_financials = False
        has_ratios = False

        for heading in soup.find_all(["h1", "h2", "h3"]):
            text = heading.get_text(strip=True).lower()
            if "financials" in text:
                has_financials = True
            if "ratios" in text:
                has_ratios = True

        if not has_financials:
            result.validation_errors.append("Financials section not found")
        if not has_ratios:
            result.validation_errors.append("Ratios section not found")

        tables = soup.find_all("table")
        if len(tables) < 2:
            result.validation_errors.append(
                f"Insufficient tables found: {len(tables)}, expected at least 2"
            )

        return has_financials or has_ratios

    def _extract_annual_financials(
        self, soup: BeautifulSoup, result: StockPageFinancials
    ) -> None:
        """Extract annual financial data (Sales, Profit after Taxation, EPS)."""
        financials_table = self._find_financials_table(soup, is_quarterly=False)
        if not financials_table:
            result.validation_errors.append("Annual financials table not found")
            return

        years = self._extract_table_headers(financials_table)
        if not years:
            result.validation_errors.append("No year headers found in annual table")
            return

        rows = financials_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            metric_name = cells[0].get_text(strip=True)
            normalized_metric = self._normalize_metric_name(metric_name)
            if not normalized_metric:
                continue

            for idx, year in enumerate(years):
                if idx + 1 >= len(cells):
                    break
                value = self._parse_numeric_value(cells[idx + 1].get_text(strip=True))
                if year not in result.annual_data:
                    result.annual_data[year] = {}
                result.annual_data[year][normalized_metric] = value

    def _extract_quarterly_financials(
        self, soup: BeautifulSoup, result: StockPageFinancials
    ) -> None:
        """Extract quarterly financial data."""
        financials_table = self._find_financials_table(soup, is_quarterly=True)
        if not financials_table:
            return

        periods = self._extract_table_headers(financials_table)
        if not periods:
            return

        rows = financials_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            metric_name = cells[0].get_text(strip=True)
            normalized_metric = self._normalize_metric_name(metric_name)
            if not normalized_metric:
                continue

            for idx, period in enumerate(periods):
                if idx + 1 >= len(cells):
                    break
                value = self._parse_numeric_value(cells[idx + 1].get_text(strip=True))
                if period not in result.quarterly_data:
                    result.quarterly_data[period] = {}
                result.quarterly_data[period][normalized_metric] = value

    def _extract_ratios(
        self, soup: BeautifulSoup, result: StockPageFinancials
    ) -> None:
        """Extract financial ratios (Net Profit Margin, EPS Growth, PEG, etc.)."""
        ratios_heading = None
        for heading in soup.find_all(["h1", "h2", "h3"]):
            if "ratios" in heading.get_text(strip=True).lower():
                ratios_heading = heading
                break

        if not ratios_heading:
            result.validation_errors.append("Ratios heading not found")
            return

        ratios_table = ratios_heading.find_next("table")
        if not ratios_table:
            result.validation_errors.append("Ratios table not found")
            return

        years = self._extract_table_headers(ratios_table)
        if not years:
            result.validation_errors.append("No year headers found in ratios table")
            return

        rows = ratios_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            metric_name = cells[0].get_text(strip=True)
            normalized_metric = self._normalize_ratio_name(metric_name)
            if not normalized_metric:
                continue

            for idx, year in enumerate(years):
                if idx + 1 >= len(cells):
                    break
                value = self._parse_numeric_value(cells[idx + 1].get_text(strip=True))
                if year not in result.ratios:
                    result.ratios[year] = {}
                result.ratios[year][normalized_metric] = value

    def _find_financials_table(
        self, soup: BeautifulSoup, is_quarterly: bool
    ) -> Optional[BeautifulSoup]:
        """Find the financials table (annual or quarterly)."""
        financials_heading = None
        for heading in soup.find_all(["h1", "h2", "h3"]):
            if "financials" in heading.get_text(strip=True).lower():
                financials_heading = heading
                break

        if not financials_heading:
            return None

        container = financials_heading.find_parent()
        if not container:
            return None

        tables = container.find_all("table")
        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue

            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            has_quarterly_pattern = any(
                re.match(r"Q\d\s+\d{4}", h) for h in headers
            )

            if is_quarterly and has_quarterly_pattern:
                return table
            elif not is_quarterly and not has_quarterly_pattern:
                has_year_pattern = any(re.match(r"^\d{4}$", h) for h in headers)
                if has_year_pattern:
                    return table

        return None

    def _extract_table_headers(self, table: BeautifulSoup) -> List[str]:
        """Extract column headers (years or quarters) from table."""
        header_row = table.find("tr")
        if not header_row:
            return []

        headers = []
        for cell in header_row.find_all(["th", "td"])[1:]:
            text = cell.get_text(strip=True)
            if text:
                headers.append(text)
        return headers

    def _normalize_metric_name(self, name: str) -> Optional[str]:
        """Normalize financial metric name to standard key."""
        name_lower = name.lower().strip()

        if "sales" in name_lower or "total income" in name_lower:
            return "sales"
        if "profit after" in name_lower or "net income" in name_lower:
            return "profit_after_tax"
        if name_lower == "eps" or "earnings per share" in name_lower:
            return "eps"

        return None

    def _normalize_ratio_name(self, name: str) -> Optional[str]:
        """Normalize ratio name to standard key."""
        name_lower = name.lower().strip()

        if "gross profit margin" in name_lower:
            return "gross_profit_margin"
        if "net profit margin" in name_lower:
            return "net_profit_margin"
        if "eps growth" in name_lower:
            return "eps_growth"
        if name_lower == "peg" or "peg ratio" in name_lower:
            return "peg"

        return None

    def _parse_numeric_value(self, text: str) -> Optional[float]:
        """Parse numeric value from text, handling parentheses for negatives."""
        if not text or text == "-" or text.lower() == "n/a":
            return None

        text = text.strip()
        is_negative = text.startswith("(") and text.endswith(")")
        if is_negative:
            text = text[1:-1]

        text = text.replace(",", "").replace("%", "").strip()

        try:
            value = float(text)
            return -value if is_negative else value
        except ValueError:
            return None

    def _validate_data(self, result: StockPageFinancials) -> bool:
        """Validate extracted data for completeness and reliability."""
        is_valid = True

        if len(result.annual_data) < self.MINIMUM_ANNUAL_YEARS:
            result.validation_errors.append(
                f"Insufficient annual data: {len(result.annual_data)} years, "
                f"minimum {self.MINIMUM_ANNUAL_YEARS}"
            )
            is_valid = False

        for year, metrics in result.annual_data.items():
            valid_metrics = sum(1 for v in metrics.values() if v is not None)
            if valid_metrics < self.MINIMUM_METRICS_PER_PERIOD:
                result.validation_errors.append(
                    f"Insufficient metrics for year {year}: {valid_metrics}"
                )
                is_valid = False

        if not self._validate_metric_ranges(result):
            is_valid = False

        if not self._cross_validate_metrics(result):
            is_valid = False

        return is_valid

    def _validate_metric_ranges(self, result: StockPageFinancials) -> bool:
        """Validate that metrics are within reasonable ranges."""
        is_valid = True

        for year, metrics in result.annual_data.items():
            sales = metrics.get("sales")
            profit = metrics.get("profit_after_tax")

            if sales is not None and sales < 0:
                result.validation_errors.append(
                    f"Invalid negative sales for {year}: {sales}"
                )
                is_valid = False

            if sales is not None and profit is not None:
                if sales > 0 and abs(profit / sales) > 10:
                    result.validation_errors.append(
                        f"Suspicious profit/sales ratio for {year}: "
                        f"{profit/sales:.2f}"
                    )

        for year, ratios in result.ratios.items():
            npm = ratios.get("net_profit_margin")
            if npm is not None and (npm < -100 or npm > 100):
                result.validation_errors.append(
                    f"Net profit margin out of range for {year}: {npm}%"
                )
                is_valid = False

        return is_valid

    def _cross_validate_metrics(self, result: StockPageFinancials) -> bool:
        """Cross-validate related metrics for consistency."""
        for year, metrics in result.annual_data.items():
            sales = metrics.get("sales")
            profit = metrics.get("profit_after_tax")

            if year in result.ratios:
                npm = result.ratios[year].get("net_profit_margin")

                if sales and profit and npm is not None and sales > 0:
                    calculated_npm = (profit / sales) * 100
                    if abs(calculated_npm - npm) > 5:
                        _logger.debug(
                            f"NPM mismatch for {year}: calculated={calculated_npm:.2f}, "
                            f"reported={npm:.2f}"
                        )

        return True

    def get_latest_annual_data(
        self, financials: StockPageFinancials
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent annual data."""
        if not financials.annual_data:
            return None

        years = sorted(financials.annual_data.keys(), reverse=True)
        if years:
            latest_year = years[0]
            return {
                "year": latest_year,
                "metrics": financials.annual_data[latest_year],
                "ratios": financials.ratios.get(latest_year, {}),
            }
        return None

    def get_latest_quarterly_data(
        self, financials: StockPageFinancials
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent quarterly data."""
        if not financials.quarterly_data:
            return None

        def parse_quarter(q: str) -> tuple:
            match = re.match(r"Q(\d)\s+(\d{4})", q)
            if match:
                return (int(match.group(2)), int(match.group(1)))
            return (0, 0)

        periods = sorted(
            financials.quarterly_data.keys(), key=parse_quarter, reverse=True
        )
        if periods:
            latest_period = periods[0]
            return {
                "period": latest_period,
                "metrics": financials.quarterly_data[latest_period],
            }
        return None


_service_instance: Optional[StockPageService] = None


def get_stock_page_service() -> StockPageService:
    """Get singleton instance of StockPageService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StockPageService()
    return _service_instance

