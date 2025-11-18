"""Format step for LangGraph workflow."""

from typing import Dict, Any, List
from financial.langgraph.state import AnalysisState
from financial.langgraph.workflow_steps.base_step import BaseWorkflowStep


class FormatStep(BaseWorkflowStep):
    """Step 5: Format final report."""
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute formatting step."""
        try:
            extracted = state.get("extracted_data") or {}
            calculated = state.get("calculated_metrics") or {}
            analysis = state.get("analysis_results") or {}
            
            if not isinstance(extracted, dict):
                extracted = {}
            if not isinstance(calculated, dict):
                calculated = {}
            if not isinstance(analysis, dict):
                analysis = {}
            
            report_lines = []
            self._format_company_info(extracted, report_lines)
            self._format_growth_metrics(calculated, report_lines)
            self._format_investment_analysis(extracted, analysis, report_lines)
            self._format_dividend_analysis(extracted, analysis, report_lines)
            self._format_valuation_metrics(extracted, calculated, analysis, report_lines)
            self._format_financial_health(calculated, report_lines)
            self._format_initiatives(analysis, report_lines)
            self._format_summary(analysis, report_lines)
            self._format_red_flags(analysis, report_lines)
            
            state["final_report"] = "\n".join(report_lines)
            
        except Exception as e:
            self._handle_errors(state, e, "final_report", "", "Report formatting error: ")
        
        self._save_state(state, "05_format")
        return state
    
    def _format_company_info(self, extracted: Dict[str, Any], report_lines: List[str]) -> None:
        """Format company information section."""
        report_lines.append("COMPANY INFORMATION:")
        report_lines.append(f"- Company Name: {extracted.get('company_name', 'N/A')}")
        report_lines.append(f"- Fiscal Year: {extracted.get('fiscal_year', 'N/A')}")
        report_lines.append(f"- Currency: {extracted.get('currency', 'N/A')}")
        report_lines.append("")
    
    def _format_growth_metrics(self, calculated: Dict[str, Any], report_lines: List[str]) -> None:
        """Format growth metrics section."""
        report_lines.append("GROWTH METRICS:")
        revenue_growth = calculated.get('revenue_growth_pct')
        if revenue_growth is not None:
            report_lines.append(f"- Revenue Growth: {revenue_growth:.2f}%")
        else:
            report_lines.append("- Revenue Growth: N/A")
        
        net_income_growth = calculated.get('net_income_growth_pct')
        if net_income_growth is not None:
            report_lines.append(f"- Net Income Growth: {net_income_growth:.2f}%")
        else:
            report_lines.append("- Net Income Growth: N/A")
        report_lines.append("")
    
    def _format_investment_analysis(self, extracted: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format investment analysis section."""
        inv_analysis = analysis.get("investment_analysis", {})
        report_lines.append("INVESTMENT ANALYSIS:")
        report_lines.append(f"- Capital Expenditures: {extracted.get('capital_expenditures', 'N/A')}")
        report_lines.append(f"- CapEx as % of Revenue: {inv_analysis.get('capex_pct_revenue', 'N/A')}%")
        report_lines.append(f"- Investment Trend: {inv_analysis.get('investment_trend', 'N/A')}")
        report_lines.append(f"- EPS (Latest): {extracted.get('eps', 'N/A')}")
        report_lines.append("")
    
    def _format_dividend_analysis(self, extracted: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format dividend analysis section."""
        div_analysis = analysis.get("dividend_analysis", {})
        report_lines.append("DIVIDEND ANALYSIS:")
        report_lines.append(f"- Dividends Paid: {extracted.get('dividends_paid', 'N/A')}")
        report_lines.append(f"- Payout Ratio: {div_analysis.get('payout_ratio', 'N/A')}%")
        report_lines.append(f"- FCF Coverage: {div_analysis.get('fcf_coverage', 'N/A')}x")
        report_lines.append(f"- Strategy: {div_analysis.get('strategy', 'N/A')}")
        report_lines.append("")
    
    def _format_valuation_metrics(self, extracted: Dict[str, Any], calculated: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format valuation metrics section."""
        val_metrics = analysis.get("valuation_metrics", {})
        report_lines.append("VALUATION METRICS:")
        report_lines.append(f"- P/E Ratio: {val_metrics.get('pe_ratio', 'N/A')}")
        
        book_value = extracted.get("book_value_per_share") or calculated.get("book_value_per_share")
        if book_value is not None:
            report_lines.append(f"- Book Value per Share: {book_value:.2f}")
        else:
            report_lines.append("- Book Value per Share: N/A")
        
        report_lines.append(f"- P/B Ratio: {val_metrics.get('pb_ratio', 'N/A')}")
        ps_ratio = calculated.get('ps_ratio')
        if ps_ratio is not None:
            report_lines.append(f"- P/S Ratio: {ps_ratio:.2f}")
        else:
            report_lines.append("- P/S Ratio: N/A")
        report_lines.append(f"- EPS: {extracted.get('eps', 'N/A')}")
        report_lines.append(f"- EV/EBITDA: {val_metrics.get('ev_ebitda', 'N/A')}")
        report_lines.append(f"- FCF Yield: {val_metrics.get('fcf_yield', 'N/A')}%")
        report_lines.append("")
    
    def _format_financial_health(self, calculated: Dict[str, Any], report_lines: List[str]) -> None:
        """Format financial health section."""
        report_lines.append("FINANCIAL HEALTH:")
        working_capital = calculated.get('working_capital')
        if working_capital is not None:
            report_lines.append(f"- Working Capital: {working_capital:,.0f}")
        else:
            report_lines.append("- Working Capital: N/A")
        
        cash_per_share = calculated.get('cash_per_share')
        if cash_per_share is not None:
            report_lines.append(f"- Cash per Share: {cash_per_share:.2f}")
        else:
            report_lines.append("- Cash per Share: N/A")
        
        debt_to_assets = calculated.get('debt_to_assets')
        if debt_to_assets is not None:
            report_lines.append(f"- Debt-to-Assets Ratio: {debt_to_assets:.3f}")
        else:
            report_lines.append("- Debt-to-Assets Ratio: N/A")
        
        quick_ratio = calculated.get('quick_ratio')
        if quick_ratio is not None:
            report_lines.append(f"- Quick Ratio: {quick_ratio:.2f}")
        else:
            report_lines.append("- Quick Ratio: N/A")
        
        gross_margin = calculated.get('gross_margin_pct')
        if gross_margin is not None:
            report_lines.append(f"- Gross Margin: {gross_margin:.2f}%")
        else:
            report_lines.append("- Gross Margin: N/A")
        
        interest_coverage = calculated.get('interest_coverage')
        if interest_coverage is not None:
            report_lines.append(f"- Interest Coverage: {interest_coverage:.2f}x")
        else:
            report_lines.append("- Interest Coverage: N/A")
        report_lines.append("")
    
    def _format_initiatives(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format new initiatives section."""
        new_initiatives = analysis.get("new_initiatives", [])
        if new_initiatives:
            report_lines.append("NEW INITIATIVES:")
            for initiative in new_initiatives:
                report_lines.append(f"- {initiative}")
            report_lines.append("")
    
    def _format_summary(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format investor summary section."""
        summary = analysis.get("investor_summary", "")
        if summary:
            report_lines.append("INVESTOR SUMMARY:")
            report_lines.append(summary)
            report_lines.append("")
    
    def _format_red_flags(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        """Format red flags section."""
        red_flags = analysis.get("red_flags", [])
        if red_flags:
            report_lines.append("RED FLAGS:")
            for flag in red_flags:
                report_lines.append(f"- {flag}")
            report_lines.append("")

