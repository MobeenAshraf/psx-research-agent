"""Shared financial service for fetching company reports from PSX."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from models.financial_data import FinancialData
from financial.services.report_sources import ISSUER_REPORTS
from financial.services.stock_page_service import (
    StockPageService,
    get_stock_page_service,
)

_logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
PSX_ORIGIN = "https://dps.psx.com.pk"
BASE_REPORTS_URL = f"{PSX_ORIGIN}/company/reports"
ANNOUNCEMENT_PERIOD = re.compile(
    r"\b(?:[A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2})\b"
)


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
        """Check the PSX reports table, then its public company announcements."""
        symbol = symbol.strip().upper()
        encoded_symbol = quote(symbol, safe="")
        sources = (
            (f"{self.base_url}/{encoded_symbol}", self._parse_report_table),
            (f"{PSX_ORIGIN}/company/{encoded_symbol}", self._parse_announcements),
        )
        available = False
        reports = []
        for url, parse in sources:
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                available = True
                reports = parse(BeautifulSoup(response.content, "html.parser"))
            except requests.RequestException as error:
                _logger.warning("Report listing unavailable for %s at %s: %s", symbol, url, error)
            if reports:
                break

        issuer = ISSUER_REPORTS.get(symbol)
        if issuer:
            issuer_period = self.parse_report_date(issuer["period_ended"])
            same_period = next(
                (report for report in reports
                 if self.parse_report_date(report["period_ended"]) == issuer_period
                 and "quarter" in report["type"].casefold()),
                None,
            )
            if same_period is not None:
                same_period.update(url=issuer["url"], source="issuer")
            else:
                reports.append({**issuer, "source": "issuer", "posting_date_str": issuer["posting_date"].date().isoformat()})
        if not reports and not available:
            raise ValueError(f"PSX filing sources are unavailable for {symbol}")

        reports.sort(key=lambda item: (
            self.parse_report_date(item["period_ended"]) or datetime.min,
            item["posting_date"] or datetime.min,
        ), reverse=True)
        return reports

    def _parse_report_table(self, soup):
        reports = []
        table = soup.find("table")
        if table is None:
            return reports
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            kind, period, posting = [cell.get_text(" ", strip=True) for cell in cells[:3]]
            link = cells[0].select_one('a[href$=".pdf"]')
            record = self._psx_record(kind, period, posting, link)
            if record is not None:
                reports.append(record)
        return reports

    def _parse_announcements(self, soup):
        reports = []
        for row in soup.find_all("tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 3:
                continue
            posting, title = (cell.get_text(" ", strip=True) for cell in cells[:2])
            normalized = title.casefold()
            if "transmission" not in normalized or not any(
                term in normalized for term in ("report", "financial statement")
            ):
                continue
            kind = next(
                (label for phrase, label in (
                    ("half year", "Half-Yearly Report"), ("quarter", "Quarterly Report"), ("annual", "Annual Report")
                ) if phrase in normalized.replace("-", " ")),
                None,
            )
            period = ANNOUNCEMENT_PERIOD.search(title)
            if kind is not None and period is not None:
                record = self._psx_record(kind, period.group(), posting, cells[2].select_one('a[href$=".pdf"]'))
                if record is not None:
                    reports.append(record)
        return reports

    def _psx_record(self, kind, period, posting, link):
        parsed_period = self.parse_report_date(period)
        if not kind or link is None or parsed_period is None:
            return None
        url = urljoin(PSX_ORIGIN, link["href"])
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "dps.psx.com.pk" or not parsed.path.lower().endswith(".pdf"):
            return None
        return {
            "type": kind,
            "period_ended": parsed_period.date().isoformat(),
            "posting_date": self.parse_report_date(posting),
            "posting_date_str": posting,
            "url": url,
            "source": "PSX",
        }

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
            report_source=latest.get("source", "PSX"),
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
    def parse_report_date(raw: str) -> Optional[datetime]:
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%B %d %Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt)
            except ValueError:
                continue
        return None


