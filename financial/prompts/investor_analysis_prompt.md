# Investor Analysis - 2-3 Line Summary

**Goal:** Provide concise, actionable investor summary answering key questions.

## Key Questions to Answer

1. **Are they investing in business? How much?**
   - CapEx analysis
   - CapEx as % of Revenue
   - Investment trend

2. **Dividends vs Growth Investment?**
   - Payout ratio
   - FCF coverage
   - Strategy: paying dividends or reinvesting?
   - **CRITICAL: Incorporate dividend_statements from extracted_data** - use these statements to explain dividend policy changes and reasons

3. **New Products/Categories/Initiatives?**
   - What new initiatives mentioned?
   - Capital allocated?
   - **CRITICAL: Extract 1-2 line summaries of investment/growth areas** - incorporate investor_statements from extracted_data

4. **Key Valuation Metrics**
   - P/E Ratio
   - P/B Ratio
   - EV/EBITDA (if available)
   - FCF Yield

5. **What investors need to know**
   - 2-3 line summary
   - Critical numbers
   - Red flags or opportunities

6. **Company Type Analysis**
   - Detect if holding company (from financial structure: high investment income, subsidiaries mentioned)
   - If holding company: extract focus areas (subsidiaries, investments, strategic focus)
   - Identify any loss-making areas/segments/expenses (even if company is profitable overall)

## Output Format

Return structured JSON:

```json
{{
  "investment_analysis": {{
    "capex": number,
    "capex_pct_revenue": number,
    "is_investing": boolean,
    "investment_trend": "increasing" | "decreasing" | "stable"
  }},
  "dividend_analysis": {{
    "dividends_paid": number,
    "payout_ratio": number,
    "fcf_coverage": number,
    "strategy": "dividend" | "growth" | "balanced",
    "dividend_statements": ["string"],
    "dividend_explanation": "1-2 line summary incorporating dividend_statements"
  }},
  "new_initiatives": ["string"],
  "investment_growth_areas": ["string"],
  "company_type": "holding" | "operating" | "mixed" | null,
  "holding_focus_areas": ["string"],
  "loss_causing_areas": ["string"],
  "key_investor_statements": ["string"],
  "valuation_metrics": {{
    "pe_ratio": number,
    "pb_ratio": number,
    "ev_ebitda": number,
    "fcf_yield": number
  }},
  "investor_summary": "2-3 line summary of everything important for investors",
  "red_flags": ["string"],
  "opportunities": ["string"]
}}
```

## Instructions

- **Be concise** - 2-3 lines for summary
- **Focus on numbers** - P/E, CapEx, Dividends, etc.
- **No fluff** - ignore management promises, CSR, marketing
- **Actionable** - what investors need to know to make decisions

## Critical Requirements

1. **Incorporate dividend_statements and investor_statements from extracted_data**
   - Use dividend_statements to populate dividend_analysis.dividend_statements
   - Create dividend_analysis.dividend_explanation incorporating these statements
   - Use investor_statements to inform investment_growth_areas and key_investor_statements

2. **Company Type Detection**
   - Analyze financial structure to detect holding company (high investment income, subsidiaries)
   - Set company_type: "holding" if primarily investment income, "operating" if operational revenue, "mixed" if both
   - Only populate holding_focus_areas if company_type is "holding" or "mixed"

3. **Loss Analysis**
   - Populate loss_causing_areas for any loss-making segments, divisions, or areas (even if company is profitable overall)
   - Analyze segment-wise data (if available) AND income statement line items
   - Priority: segment data if available, otherwise income statement items

4. **Investment/Growth Areas**
   - Extract 1-2 line summaries from investor_statements and analysis
   - Focus on concrete investment priorities and growth initiatives

