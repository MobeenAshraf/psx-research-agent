"""Normalize statement inputs before applying financial formulas."""

from datetime import date
from math import isfinite


AMOUNT_FIELDS = {
    "net_income", "net_income_previous", "cash", "total_debt",
    "operating_cash_flow", "free_cash_flow", "capital_expenditures", "dividends_paid",
    "shareholders_equity", "total_equity", "total_assets", "total_liabilities",
    "current_assets", "current_liabilities", "operating_income", "operating_income_previous",
    "ebitda", "cogs", "accounts_receivable", "inventory", "interest_expense",
    "beginning_cash", "net_change_cash", "cash_fx_effect", "ending_cash", "cash_flow_net_income",
    "ttm_revenue", "ttm_ebitda", "ttm_operating_cash_flow", "ttm_capital_expenditures",
}
POSITIVE_EXPENSE_FIELDS = {
    "capital_expenditures", "dividends_paid", "cogs", "interest_expense",
    "ttm_capital_expenditures",
}
UNSCALED_FIELDS = {"eps", "book_value_per_share", "shares_outstanding", "ttm_eps"}


def finite_number(value):
    return type(value) is int or (type(value) is float and isfinite(value))


def normalize_statement(extracted: dict) -> dict:
    """Convert monetary totals to currency units and retain the original reporting scale."""
    scale = extracted.get("monetary_scale")
    if not finite_number(scale) or scale not in {1, 1_000, 1_000_000, 1_000_000_000}:
        raise ValueError("The filing's monetary scale could not be verified")
    currency = extracted.get("currency")
    if not isinstance(currency, str) or len(currency.strip()) != 3 or not currency.strip().isalpha():
        raise ValueError("The filing's currency could not be verified")
    months = extracted.get("period_months")
    if type(months) is not int or months not in {3, 6, 9, 12}:
        raise ValueError("The duration of the filing's financial statements could not be verified")

    try:
        period_end = date.fromisoformat(extracted["period_end"]).isoformat()
    except (KeyError, TypeError, ValueError):
        raise ValueError("The filing's period end could not be verified") from None
    if extracted.get("reporting_scope") not in ("standalone", "consolidated"):
        raise ValueError("The filing's statement scope could not be verified")

    def amount(value, key):
        if not finite_number(value):
            return None
        scaled = (abs(value) if key in POSITIVE_EXPENSE_FIELDS else value) * scale
        return scaled if finite_number(scaled) else None

    data = dict(extracted)
    data.update(
        currency=currency.strip().upper(), period_end=period_end,
        monetary_scale=1, reported_monetary_scale=scale,
    )
    for key in sorted(AMOUNT_FIELDS):
        data[key] = amount(data.get(key), key)
    for key in sorted(UNSCALED_FIELDS):
        if not finite_number(data.get(key)):
            data[key] = None

    revenue = data.get("revenue")
    data["revenue"] = {
        label: amount(revenue.get(label), "revenue") if isinstance(revenue, dict) else None
        for label in ("current", "previous")
    }
    for field, keys in (
        ("segment_data", ("revenue", "operating_income")),
        ("other_income_breakdown", ("value",)),
    ):
        data[field] = [
            {**row, **{key: amount(row.get(key), key) for key in keys}}
            for row in (data.get(field) or []) if isinstance(row, dict)
        ]
    return data
