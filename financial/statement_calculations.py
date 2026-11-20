"""Deterministic formulas for normalized financial statements."""

from financial.statement_values import finite_number


def calculate_metrics(data: dict, stock_price=None) -> dict:
    calculated = {}
    revenue_data = data["revenue"]
    revenue = revenue_data["current"]
    net_income = data["net_income"]
    cash = data["cash"]
    debt = data["total_debt"]
    equity = data["shareholders_equity"]
    assets = data["total_assets"]
    liabilities = data["current_liabilities"]
    current_assets = data["current_assets"]
    capex = data["capital_expenditures"]
    dividends = data["dividends_paid"]
    operating_cf = data["operating_cash_flow"]

    def ratio(key, numerator, denominator, multiplier=1):
        if numerator is not None and denominator is not None and denominator > 0:
            calculated[key] = multiplier * numerator / denominator

    def difference(left, right):
        return left - right if left is not None and right is not None else None

    free_cash_flow = difference(operating_cf, capex)
    if free_cash_flow is not None:
        calculated["free_cash_flow"] = free_cash_flow
    for key, current, previous in (
        ("revenue_growth_pct", revenue, revenue_data["previous"]),
        ("net_income_growth_pct", net_income, data["net_income_previous"]),
    ):
        ratio(key, difference(current, previous), previous, 100)

    ratio("roe", net_income, equity, 100)
    ratio("roa", net_income, assets, 100)
    ratio("debt_to_equity", debt, equity)
    ratio("debt_to_assets", debt, assets)
    ratio("current_ratio", current_assets, liabilities)
    working_capital = difference(current_assets, liabilities)
    if working_capital is not None:
        calculated["working_capital"] = working_capital
    receivables = data["accounts_receivable"]
    if cash is not None and receivables is not None:
        ratio("quick_ratio", cash + receivables, liabilities)
    ratio("operating_margin", data["operating_income"], revenue, 100)
    ratio("net_margin", net_income, revenue, 100)
    ratio("gross_margin_pct", difference(revenue, data["cogs"]), revenue, 100)
    ratio("capex_pct_revenue", capex, revenue, 100)
    ratio("payout_ratio", dividends, net_income, 100)
    ratio("fcf_coverage", free_cash_flow, dividends)
    ratio("interest_coverage", data["operating_income"], data["interest_expense"])

    def share_of(numerator, denominator):
        if numerator is not None and denominator is not None and denominator > 0:
            return 100 * numerator / denominator
        return None

    other_income = [
        {**row, "pct_of_net_income": share_of(row["value"], net_income)}
        for row in data["other_income_breakdown"] if row["value"] is not None
    ]
    other_income_total = sum(row["value"] for row in other_income) if other_income else None
    calculated["income_composition"] = {
        "segments": [
            {
                **row,
                "revenue_pct": share_of(row["revenue"], revenue),
                "income_pct": share_of(row["operating_income"], data["operating_income"]),
            }
            for row in data["segment_data"]
        ],
        "other_income": {
            "total": other_income_total,
            "pct_of_net_income": share_of(other_income_total, net_income),
            "breakdown": other_income,
        },
    }

    shares = data["shares_outstanding"]
    ratio("cash_per_share", cash, shares)
    book_value = data["book_value_per_share"]
    if book_value is None and shares is not None and shares > 0 and equity is not None:
        book_value = equity / shares
    if book_value is not None:
        calculated["book_value_per_share"] = book_value

    if data["currency"] != "PKR" or not finite_number(stock_price) or stock_price <= 0:
        return calculated

    annual = data["period_months"] == 12
    ttm_eps = data["eps"] if annual else data["ttm_eps"]
    ttm_revenue = revenue if annual else data["ttm_revenue"]
    ttm_ebitda = data["ebitda"] if annual else data["ttm_ebitda"]
    ttm_fcf = free_cash_flow if annual else difference(
        data["ttm_operating_cash_flow"], data["ttm_capital_expenditures"]
    )
    ratio("pe_ratio", stock_price, ttm_eps)
    ratio("pb_ratio", stock_price, book_value)
    if shares is not None and shares > 0:
        market_cap = stock_price * shares
        calculated["market_cap"] = market_cap
        ratio("ps_ratio", market_cap, ttm_revenue)
        ratio("fcf_yield", ttm_fcf, market_cap, 100)
        # Consolidated EBITDA includes subsidiaries. Include their non-controlling
        # interests when reported, or leave enterprise value unavailable.
        total_equity = data["total_equity"]
        if data.get("reporting_scope") == "standalone":
            minority_interest = 0
        elif total_equity is not None and equity is not None and total_equity >= equity:
            minority_interest = total_equity - equity
        else:
            minority_interest = None
        if debt is not None and cash is not None and minority_interest is not None:
            enterprise_value = market_cap + debt + minority_interest - cash
            ratio("ev_ebitda", enterprise_value, ttm_ebitda)
    return calculated
