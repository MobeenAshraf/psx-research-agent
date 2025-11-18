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

3. **New Products/Categories/Initiatives?**
   - What new initiatives mentioned?
   - Capital allocated?

4. **Key Valuation Metrics**
   - P/E Ratio
   - P/B Ratio
   - EV/EBITDA (if available)
   - FCF Yield

5. **What investors need to know**
   - 2-3 line summary
   - Critical numbers
   - Red flags or opportunities

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
    "strategy": "dividend" | "growth" | "balanced"
  }},
  "new_initiatives": ["string"],
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

