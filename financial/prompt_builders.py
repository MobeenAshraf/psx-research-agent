"""Prompt construction shared by the app and the model benchmark."""

import json

DEFAULT_SYSTEM_PROMPT = (
    "You are a financial data extraction and analysis specialist. "
    "Extract accurate numerical data and provide insightful analysis."
)


def build_pdf_extraction_prompt(extraction_prompt_content: str, stock_price_str: str) -> str:
    return f"""{extraction_prompt_content}{stock_price_str}

**YOUR TASK:**
Extract all financial data from the PDF document and return it as a valid JSON object matching the required schema.

**CRITICAL REQUIREMENTS:**
1. Return ONLY valid JSON - no markdown code blocks, no explanations, no additional text
2. Use numbers (not strings) for all monetary values
3. Use null for missing values (never use 0 or empty string as placeholder)
4. Search ALL sections: Income Statement, Balance Sheet, Cash Flow Statement, Notes
5. Extract exact values as stated in the document - do not estimate or calculate unless explicitly instructed
6. Read the PDF carefully - look for tables, financial statements, and numerical data

Return the JSON object now:"""


def build_analysis_prompt(analysis_prompt_content: str, state: dict) -> str:
    extracted = state.get("extracted_data", {})
    calculated = state.get("calculated_metrics", {})

    if not isinstance(extracted, dict):
        extracted = {}
    if not isinstance(calculated, dict):
        calculated = {}

    dividend_statements = extracted.get("dividend_statements")
    if not isinstance(dividend_statements, list):
        dividend_statements = []

    investor_statements = extracted.get("investor_statements")
    if not isinstance(investor_statements, list):
        investor_statements = []

    extracted_json_str = json.dumps(extracted, indent=2)
    calculated_json_str = json.dumps(calculated, indent=2)
    extracted_json_str = extracted_json_str.replace("{", "{{").replace("}", "}}")
    calculated_json_str = calculated_json_str.replace("{", "{{").replace("}", "}}")

    statements_context = ""
    if dividend_statements or investor_statements:
        statements_context = "\n\n**CRITICAL: Investor Statements from Extraction:**\n"
        if dividend_statements:
            statements_context += f"dividend_statements: {json.dumps(dividend_statements, indent=2)}\n"
        if investor_statements:
            statements_context += f"investor_statements: {json.dumps(investor_statements, indent=2)}\n"
        statements_context += "\n**You MUST incorporate these statements into your analysis.**"

    stock_page_context = _stock_page_context(state)

    return f"""{analysis_prompt_content}

Extracted Data:
{extracted_json_str}

Calculated Metrics:
{calculated_json_str}{statements_context}{stock_page_context}

Provide investor-focused analysis as structured JSON. Return ONLY valid JSON, no additional text."""


def _stock_page_context(state: dict) -> str:
    """Build context string from stock page data for LLM prompt."""
    stock_page_context = state.get("stock_page_context")
    if not stock_page_context:
        return ""

    context_parts = ["\n\n**PSX Stock Page Financial Data (Capital Stake):**"]

    annual = stock_page_context.get("annual_financials", {})
    if annual:
        context_parts.append("\n**Annual Financials (000's):**")
        years = sorted(annual.keys(), reverse=True)
        for year in years[:4]:
            metrics = annual[year]
            metrics_str = ", ".join(
                f"{k}: {v:,.0f}" if v is not None else f"{k}: N/A"
                for k, v in metrics.items()
            )
            context_parts.append(f"  {year}: {metrics_str}")

    quarterly = stock_page_context.get("quarterly_financials", {})
    if quarterly:
        context_parts.append("\n**Quarterly Financials (000's):**")
        periods = sorted(quarterly.keys(), reverse=True)
        for period in periods[:4]:
            metrics = quarterly[period]
            metrics_str = ", ".join(
                f"{k}: {v:,.0f}" if v is not None else f"{k}: N/A"
                for k, v in metrics.items()
            )
            context_parts.append(f"  {period}: {metrics_str}")

    ratios = stock_page_context.get("ratios", {})
    if ratios:
        context_parts.append("\n**Financial Ratios (%):**")
        ratio_labels = {
            "peg": "PEG (Price/Earnings to Growth)",
            "eps_growth": "EPS Growth",
            "net_profit_margin": "Net Profit Margin",
            "gross_profit_margin": "Gross Profit Margin",
        }
        years = sorted(ratios.keys(), reverse=True)
        for year in years[:4]:
            year_ratios = ratios[year]
            ratios_str = ", ".join(
                f"{ratio_labels.get(k, k)}: {v:.2f}"
                if v is not None
                else f"{ratio_labels.get(k, k)}: N/A"
                for k, v in year_ratios.items()
            )
            context_parts.append(f"  {year}: {ratios_str}")

    context_parts.append(
        "\n**Use this validated data as primary reference for financial analysis.**"
    )

    return "\n".join(context_parts)


def build_decision_prompts(
    template: str,
    schema: str,
    symbol: str,
    profile: dict,
    technical: dict,
    financial_report: str,
    index_membership: dict,
) -> tuple[str, str]:
    technical_summary = f"""
Symbol: {symbol}
Recommendation: {technical.get('recommendation', 'N/A')}
Confidence: {technical.get('confidence', 0):.2f}
Key Indicators: {json.dumps(technical.get('indicators', {}), indent=2)}
Reasoning: {json.dumps(technical.get('reasoning', []), indent=2)}
"""
    values = {
        "SCHEMA": schema,
        "USER_PROFILE": json.dumps(profile, indent=2),
        "TECHNICAL_ANALYSIS_SUMMARY": technical_summary,
        "FINANCIAL_ANALYSIS_SUMMARY": financial_report[:2000],
        "INDEX_MEMBERSHIP": json.dumps(index_membership, indent=2),
    }
    for name, value in values.items():
        template = template.replace("{" + name + "_PLACEHOLDER}", value)
    return template, f"Analyze stock {symbol} and provide your investment decision."
