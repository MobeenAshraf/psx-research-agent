"""Read PSX's published eligible equities for informational display."""

from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests


ELIGIBLE_EQUITIES_URL = "https://dps.psx.com.pk/shariah/eligible-scrips"


def get_psx_shariah_status(symbol: str) -> dict:
    checked_on = datetime.now(ZoneInfo("Asia/Karachi")).date().isoformat()
    result = {"source_url": ELIGIBLE_EQUITIES_URL, "checked_on": checked_on, "status": "unavailable"}
    try:
        response = requests.get(ELIGIBLE_EQUITIES_URL, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return result

    soup = BeautifulSoup(response.content, "html.parser")
    for table in soup.find_all("table"):
        headers = [cell.get_text(strip=True).casefold() for cell in table.select("thead th")]
        if headers[:2] != ["symbol", "name"]:
            continue
        symbols = {
            row[0].get_text(strip=True).upper()
            for tr in table.select("tbody tr")
            if len(row := tr.find_all("td")) >= 2 and row[0].find("a", href=True)
        }
        if symbols:
            result["status"] = "listed" if symbol.strip().upper() in symbols else "not_listed"
        break
    return result
