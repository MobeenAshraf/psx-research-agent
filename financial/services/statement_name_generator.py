"""Utility to generate sanitized statement names."""

import re
from typing import Optional


class StatementNameGenerator:
    """Generate filesystem-friendly names for statements."""

    @staticmethod
    def generate_name(report_type: str, period_ended: str) -> str:
        type_part = StatementNameGenerator._sanitize(report_type)
        period_part = StatementNameGenerator._sanitize(period_ended)
        if period_part:
            return f"{type_part}_{period_part}"
        return type_part

    @staticmethod
    def _sanitize(value: Optional[str]) -> str:
        if not value:
            return ""
        text = str(value).strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "_", text)
        return text.strip("_")


