"""Verified issuer copies of filings for use during PSX document outages."""

from datetime import datetime


# Each entry is tied to a specific published period and must not replace a
# newer filing discovered through PSX.
ISSUER_REPORTS = {
    "LUCK": {
        "type": "Quarterly Report",
        "period_ended": "2026-09-30",
        "posting_date": datetime(2026, 10, 29),
        "url": "https://assets.lucky-cement.com/0000204815_Financial_Results_30_09_2026_2_8c1a80dbf9.pdf",
    },
    "INDU": {
        "type": "Quarterly Report",
        "period_ended": "2026-09-30",
        "posting_date": datetime(2026, 10, 30),
        "url": "https://toyota-indus.com/wp-content/uploads/2026/10/Financial-Report-for-the-Quarter-ended-September-30-2026.pdf",
    },
}
