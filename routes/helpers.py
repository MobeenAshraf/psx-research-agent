"""Shared helper functions for routes."""

from typing import Dict, Any, List
import pandas as pd


def normalize_indicators(indicators: dict) -> dict:
    """Normalize indicators by converting pandas Series to scalars."""
    normalized = indicators.copy()
    for key, value in list(normalized.items()):
        if isinstance(value, pd.Series):
            if not value.empty:
                normalized[key] = float(value.iloc[-1])
            else:
                normalized[key] = None
        elif isinstance(value, (list, tuple)) and len(value) > 0:
            normalized[key] = value[-1] if isinstance(value[-1], (int, float)) else value
        elif isinstance(value, dict):
            normalized[key] = value
        elif value is None or (isinstance(value, float) and pd.isna(value)):
            normalized[key] = None
    return normalized


def format_detailed_analysis(analysis) -> str:
    """Format analysis for display."""
    normalized_indicators = normalize_indicators(analysis.indicators)
    metrics = analysis.metrics or {}

    lines = [
        f"Symbol: {analysis.symbol}",
        f"Recommendation: {analysis.recommendation}",
        f"Confidence: {analysis.confidence:.2f}",
        "",
    ]

    index_membership = normalized_indicators.pop('index_membership', None)

    if index_membership:
        lines.append("Market Structure:")
        for index_name, data in index_membership.items():
            if data.get('included'):
                weightage = data.get('weightage')
                if weightage is not None:
                    lines.append(f"  • {index_name.upper()}: Included ({weightage:.2f}% weightage)")
                else:
                    lines.append(f"  • {index_name.upper()}: Included")
            else:
                lines.append(f"  • {index_name.upper()}: Not included")
        lines.append("")

    if metrics.get("stock_page_data_valid"):
        lines.append("Financial Metrics (PSX Stock Page):")
        if metrics.get("annual_year"):
            lines.append(f"  Year: {metrics['annual_year']}")
        if metrics.get("eps") is not None:
            lines.append(f"  EPS: {metrics['eps']:.2f}")
        if metrics.get("sales") is not None:
            lines.append(f"  Sales (000's): {metrics['sales']:,.0f}")
        if metrics.get("profit_after_tax") is not None:
            lines.append(f"  Profit After Tax (000's): {metrics['profit_after_tax']:,.0f}")
        if metrics.get("net_profit_margin") is not None:
            lines.append(f"  Net Profit Margin: {metrics['net_profit_margin']:.2f}%")
        if metrics.get("eps_growth") is not None:
            lines.append(f"  EPS Growth: {metrics['eps_growth']:.2f}%")
        if metrics.get("peg") is not None:
            lines.append(f"  PEG (Price/Earnings to Growth) Ratio: {metrics['peg']:.2f}")
        if metrics.get("gross_profit_margin") is not None:
            lines.append(f"  Gross Profit Margin: {metrics['gross_profit_margin']:.2f}%")

        if metrics.get("quarterly_period"):
            lines.append("")
            lines.append(f"  Latest Quarter ({metrics['quarterly_period']}):")
            if metrics.get("quarterly_eps") is not None:
                lines.append(f"    Quarterly EPS: {metrics['quarterly_eps']:.2f}")
            if metrics.get("quarterly_sales") is not None:
                lines.append(f"    Quarterly Sales (000's): {metrics['quarterly_sales']:,.0f}")
            if metrics.get("quarterly_profit") is not None:
                lines.append(f"    Quarterly Profit (000's): {metrics['quarterly_profit']:,.0f}")
        lines.append("")

    lines.append("Technical Indicators:")
    for key, value in normalized_indicators.items():
        if value is not None and key != 'index_membership':
            lines.append(f"  {key}: {value}")

    if analysis.reasoning:
        lines.append("")
        lines.append("Reasoning:")
        for reason in analysis.reasoning:
            lines.append(f"  - {reason}")

    return "\n".join(lines)

