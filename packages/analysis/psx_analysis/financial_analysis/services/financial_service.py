"""Shared financial service for fetching company reports from PSX."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from psx_analysis.models.financial_data import FinancialData

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_REPORTS_URL = "https://dps.psx.com.pk/company/reports"


class FinancialService:
    """Fetch and parse financial statements directly from PSX."""

    def __init__(self, base_url: str = BASE_REPORTS_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

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

    def get_latest_report(self, symbol: str) -> Optional[FinancialData]:
        """Return the newest report as FinancialData or None."""
        reports = self.fetch_company_reports(symbol)
        if not reports:
            return None

        latest = reports[0]
        posting_date = latest["posting_date"] or datetime.now()

        return FinancialData(
            symbol=symbol.upper(),
            report_type=latest["type"],
            period_ended=latest["period_ended"],
            posting_date=posting_date,
            report_url=latest["url"],
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


