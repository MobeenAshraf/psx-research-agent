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
            self._format_business_model(extracted, report_lines)
            self._format_investor_statements(extracted, report_lines)
            self._format_investment_growth_areas(analysis, report_lines)
            self._format_holding_focus_areas(analysis, report_lines)
            self._format_loss_causing_areas(extracted, analysis, report_lines)
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
    
    def _format_metric(
        self, 
        report_lines: List[str], 
        label: str, 
        value: Any, 
        format_str: str = "{:.2f}", 
        suffix: str = ""
    ) -> None:
        """Format a metric with N/A fallback."""
        if value is not None:
            report_lines.append(f"- {label}: {format_str.format(value)}{suffix}")
        else:
            report_lines.append(f"- {label}: N/A")
    
    def _format_list_section(
        self, 
        report_lines: List[str], 
        title: str, 
        items: List[str]
    ) -> None:
        """Format a list section with validation."""
        if items and isinstance(items, list) and items:
            report_lines.append(f"{title}:")
            for item in items:
                if item and isinstance(item, str) and item.strip():
                    report_lines.append(f"- {item}")
            report_lines.append("")
    
    def _format_company_info(self, extracted: Dict[str, Any], report_lines: List[str]) -> None:
        report_lines.append("COMPANY INFORMATION:")
        report_lines.append(f"- Company Name: {extracted.get('company_name', 'N/A')}")
        report_lines.append(f"- Fiscal Year: {extracted.get('fiscal_year', 'N/A')}")
        report_lines.append(f"- Currency: {extracted.get('currency', 'N/A')}")
        report_lines.append("")
    
    def _format_business_model(self, extracted: Dict[str, Any], report_lines: List[str]) -> None:
        business_model = extracted.get("business_model", [])
        if not business_model or not isinstance(business_model, list):
            return
        
        report_lines.append("BUSINESS MODEL:")
        for segment in business_model:
            if isinstance(segment, dict) and segment.get("name") and segment.get("description"):
                report_lines.append(f"- {segment['name']}: {segment['description']}")
        report_lines.append("")
    
    def _format_growth_metrics(self, calculated: Dict[str, Any], report_lines: List[str]) -> None:
        report_lines.append("GROWTH METRICS:")
        self._format_metric(report_lines, "Revenue Growth", calculated.get('revenue_growth_pct'), suffix="%")
        self._format_metric(report_lines, "Net Income Growth", calculated.get('net_income_growth_pct'), suffix="%")
        report_lines.append("")
    
    def _format_investment_analysis(self, extracted: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        inv_analysis = analysis.get("investment_analysis", {})
        report_lines.append("INVESTMENT ANALYSIS:")
        report_lines.append(f"- Capital Expenditures: {extracted.get('capital_expenditures', 'N/A')}")
        report_lines.append(f"- CapEx as % of Revenue: {inv_analysis.get('capex_pct_revenue', 'N/A')}%")
        report_lines.append(f"- Investment Trend: {inv_analysis.get('investment_trend', 'N/A')}")
        report_lines.append(f"- EPS (Latest): {extracted.get('eps', 'N/A')}")
        report_lines.append("")
    
    def _format_dividend_analysis(self, extracted: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        div_analysis = analysis.get("dividend_analysis", {})
        report_lines.append("DIVIDEND ANALYSIS:")
        report_lines.append(f"- Dividends Paid: {extracted.get('dividends_paid', 'N/A')}")
        report_lines.append(f"- Payout Ratio: {div_analysis.get('payout_ratio', 'N/A')}%")
        report_lines.append(f"- FCF Coverage: {div_analysis.get('fcf_coverage', 'N/A')}x")
        report_lines.append(f"- Strategy: {div_analysis.get('strategy', 'N/A')}")
        
        dividend_statements = div_analysis.get("dividend_statements", [])
        if dividend_statements:
            report_lines.append("")
            self._format_list_section(report_lines, "Dividend Policy Statements", dividend_statements)
        
        dividend_explanation = div_analysis.get("dividend_explanation")
        if dividend_explanation and isinstance(dividend_explanation, str) and dividend_explanation.strip():
            report_lines.append("")
            report_lines.append(f"Dividend Explanation: {dividend_explanation}")
        
        report_lines.append("")
    
    def _format_valuation_metrics(self, extracted: Dict[str, Any], calculated: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        val_metrics = analysis.get("valuation_metrics", {})
        report_lines.append("VALUATION METRICS:")
        report_lines.append(f"- P/E Ratio: {val_metrics.get('pe_ratio', 'N/A')}")
        
        book_value = extracted.get("book_value_per_share") or calculated.get("book_value_per_share")
        self._format_metric(report_lines, "Book Value per Share", book_value)
        
        report_lines.append(f"- P/B Ratio: {val_metrics.get('pb_ratio', 'N/A')}")
        self._format_metric(report_lines, "P/S Ratio", calculated.get('ps_ratio'))
        report_lines.append(f"- EPS: {extracted.get('eps', 'N/A')}")
        report_lines.append(f"- EV/EBITDA: {val_metrics.get('ev_ebitda', 'N/A')}")
        report_lines.append(f"- FCF Yield: {val_metrics.get('fcf_yield', 'N/A')}%")
        report_lines.append("")
    
    def _format_financial_health(self, calculated: Dict[str, Any], report_lines: List[str]) -> None:
        report_lines.append("FINANCIAL HEALTH:")
        self._format_metric(report_lines, "Working Capital", calculated.get('working_capital'), "{:,.0f}")
        self._format_metric(report_lines, "Cash per Share", calculated.get('cash_per_share'))
        self._format_metric(report_lines, "Debt-to-Assets Ratio", calculated.get('debt_to_assets'), "{:.3f}")
        self._format_metric(report_lines, "Quick Ratio", calculated.get('quick_ratio'))
        self._format_metric(report_lines, "Gross Margin", calculated.get('gross_margin_pct'), suffix="%")
        self._format_metric(report_lines, "Interest Coverage", calculated.get('interest_coverage'), suffix="x")
        report_lines.append("")
    
    def _format_initiatives(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        new_initiatives = analysis.get("new_initiatives", [])
        if new_initiatives:
            self._format_list_section(report_lines, "NEW INITIATIVES", new_initiatives)
    
    def _format_summary(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        summary = analysis.get("investor_summary", "")
        if summary:
            report_lines.append("INVESTOR SUMMARY:")
            report_lines.append(summary)
            report_lines.append("")
    
    def _format_red_flags(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        red_flags = analysis.get("red_flags", [])
        if red_flags:
            self._format_list_section(report_lines, "RED FLAGS", red_flags)
    
    def _format_investor_statements(self, extracted: Dict[str, Any], report_lines: List[str]) -> None:
        investor_statements = extracted.get("investor_statements", [])
        if investor_statements:
            self._format_list_section(report_lines, "KEY INVESTOR STATEMENTS", investor_statements)
    
    def _format_investment_growth_areas(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        growth_areas = analysis.get("investment_growth_areas", [])
        if growth_areas:
            self._format_list_section(report_lines, "INVESTMENT & GROWTH AREAS", growth_areas)
    
    def _format_holding_focus_areas(self, analysis: Dict[str, Any], report_lines: List[str]) -> None:
        company_type = analysis.get("company_type")
        if company_type not in ["holding", "mixed"]:
            return
        
        focus_areas = analysis.get("holding_focus_areas", [])
        if focus_areas:
            self._format_list_section(report_lines, "HOLDING COMPANY FOCUS AREAS", focus_areas)
    
    def _format_loss_causing_areas(self, extracted: Dict[str, Any], analysis: Dict[str, Any], report_lines: List[str]) -> None:
        loss_areas = analysis.get("loss_causing_areas", [])
        if loss_areas:
            self._format_list_section(report_lines, "LOSS-CAUSING AREAS", loss_areas)

