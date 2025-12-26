"""Shared financial service for fetching company reports from PSX."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from models.financial_data import FinancialData
from financial.services.stock_page_service import (
    StockPageService,
    get_stock_page_service,
)

_logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_REPORTS_URL = "https://dps.psx.com.pk/company/reports"


class FinancialService:
    """Fetch and parse financial statements directly from PSX."""

    def __init__(
        self,
        base_url: str = BASE_REPORTS_URL,
        stock_page_service: Optional[StockPageService] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._stock_page_service = stock_page_service

    def fetch_company_reports(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch available reports for a company symbol."""
        url = f"{self.base_url}/{symbol.upper()}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ValueError(f"Failed to fetch reports for {symbol}: {exc}") from exc

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        reports: List[Dict[str, Any]] = []
        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            report_type = cells[0].text.strip()
            link = cells[0].find("a")
            report_url = None
            if link and link.get("href"):
                report_url = link["href"]
                if not report_url.startswith("http"):
                    report_url = f"https://dps.psx.com.pk{report_url}"

            period_ended = cells[1].text.strip() if len(cells) > 1 else ""
            posting_date_str = cells[2].text.strip() if len(cells) > 2 else ""
            posting_date = self._parse_posting_date(posting_date_str)

            if report_type and report_url:
                reports.append(
                    {
                        "type": report_type,
                        "period_ended": period_ended,
                        "posting_date": posting_date,
                        "posting_date_str": posting_date_str,
                        "url": report_url,
                    }
                )

        reports.sort(key=lambda item: item["posting_date"] or datetime.min, reverse=True)
        return reports

    @property
    def stock_page_service(self) -> StockPageService:
        """Lazy-load stock page service."""
        if self._stock_page_service is None:
            self._stock_page_service = get_stock_page_service()
        return self._stock_page_service

    def get_latest_report(self, symbol: str) -> Optional[FinancialData]:
        """Return the newest report as FinancialData with stock page data if available."""
        symbol_upper = symbol.upper()

        reports = self.fetch_company_reports(symbol_upper)
        if not reports:
            return None

        latest = reports[0]
        posting_date = latest["posting_date"] or datetime.now()

        financial_data = FinancialData(
            symbol=symbol_upper,
            report_type=latest["type"],
            period_ended=latest["period_ended"],
            posting_date=posting_date,
            report_url=latest["url"],
        )

        self._enrich_with_stock_page_data(financial_data)

        return financial_data

    def _enrich_with_stock_page_data(self, financial_data: FinancialData) -> None:
        """Enrich FinancialData with validated stock page data if available."""
        try:
            stock_page_data = self.stock_page_service.fetch_stock_financials(
                financial_data.symbol
            )

            if stock_page_data is None or not stock_page_data.is_valid:
                _logger.info(
                    f"Stock page data not available or invalid for "
                    f"{financial_data.symbol}, using PDF-only analysis"
                )
                return

            financial_data.annual_financials = stock_page_data.annual_data
            financial_data.quarterly_financials = stock_page_data.quarterly_data
            financial_data.ratios = stock_page_data.ratios
            financial_data.stock_page_data_valid = True

            latest_annual = self.stock_page_service.get_latest_annual_data(
                stock_page_data
            )
            if latest_annual and latest_annual.get("metrics"):
                metrics = latest_annual["metrics"]
                if metrics.get("eps") is not None:
                    financial_data.eps = metrics["eps"]

            _logger.info(
                f"Enriched {financial_data.symbol} with stock page data: "
                f"{len(stock_page_data.annual_data)} years annual, "
                f"{len(stock_page_data.quarterly_data)} quarters, "
                f"{len(stock_page_data.ratios)} years ratios"
            )

        except Exception as exc:
            _logger.warning(
                f"Failed to enrich with stock page data for "
                f"{financial_data.symbol}: {exc}"
            )

    @staticmethod
    def _parse_posting_date(raw: str) -> Optional[datetime]:
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d %b %Y"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None


