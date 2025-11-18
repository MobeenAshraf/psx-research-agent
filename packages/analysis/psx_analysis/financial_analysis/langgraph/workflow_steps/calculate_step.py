"""Calculate step for LangGraph workflow."""

from psx_analysis.financial_analysis.langgraph.state import AnalysisState
from psx_analysis.financial_analysis.langgraph.workflow_steps.base_step import BaseWorkflowStep


class CalculateStep(BaseWorkflowStep):
    """Step 2: Calculate derived metrics using deterministic tools."""
    
    def execute(self, state: AnalysisState) -> AnalysisState:
        """Execute calculation step."""
        try:
            extracted = state.get("extracted_data")
            if extracted is None:
                state["errors"].append("Cannot calculate metrics: extraction data is None")
                state["calculated_metrics"] = {}
                return state
            
            if not isinstance(extracted, dict):
                state["errors"].append(f"Cannot calculate metrics: extraction data is not a dict (got {type(extracted)})")
                state["calculated_metrics"] = {}
                return state
            
            calculated = {}
            stock_price = state.get("stock_price")
            
            self._calculate_share_metrics(extracted, calculated, stock_price)
            self._calculate_valuation_metrics(extracted, calculated, stock_price)
            self._calculate_growth_metrics(extracted, calculated)
            self._calculate_health_metrics(extracted, calculated, stock_price)
            
            state["calculated_metrics"] = calculated
            
        except Exception as e:
            self._handle_errors(state, e, "calculated_metrics", {}, "Calculation error: ")
        
        self._save_state(state, "02_calculate")
        return state
    
    def _calculate_share_metrics(self, extracted: dict, calculated: dict, stock_price: float) -> None:
        """Calculate share-related metrics."""
        if "shares_outstanding" not in extracted or extracted.get("shares_outstanding") is None:
            net_income = extracted.get("net_income")
            eps = extracted.get("eps")
            if net_income and eps and eps > 0:
                calculated["shares_outstanding"] = net_income / eps
        
        shares_outstanding = extracted.get("shares_outstanding") or calculated.get("shares_outstanding")
        
        if stock_price and shares_outstanding:
            calculated["market_cap"] = stock_price * shares_outstanding
        
        if "book_value_per_share" not in extracted or extracted["book_value_per_share"] is None:
            shareholders_equity = extracted.get("shareholders_equity")
            if shareholders_equity and shares_outstanding and shares_outstanding > 0:
                calculated["book_value_per_share"] = shareholders_equity / shares_outstanding
    
    def _calculate_valuation_metrics(self, extracted: dict, calculated: dict, stock_price: float) -> None:
        """Calculate valuation metrics."""
        if stock_price and extracted.get("eps") and extracted["eps"] > 0:
            calculated["pe_ratio"] = stock_price / extracted["eps"]
        
        book_value = extracted.get("book_value_per_share") or calculated.get("book_value_per_share")
        if stock_price and book_value and book_value > 0:
            calculated["pb_ratio"] = stock_price / book_value
        
        market_cap = calculated.get("market_cap")
        revenue_data = extracted.get("revenue")
        if isinstance(revenue_data, dict):
            revenue = revenue_data.get("current")
        else:
            revenue = revenue_data
        
        if market_cap and revenue and revenue > 0:
            calculated["ps_ratio"] = market_cap / revenue
        
        ebitda = extracted.get("ebitda")
        cash = extracted.get("cash")
        total_debt = extracted.get("total_debt")
        if market_cap and total_debt and cash is not None and ebitda and ebitda > 0:
            ev = market_cap + total_debt - cash
            calculated["ev_ebitda"] = ev / ebitda
        
        free_cash_flow = extracted.get("free_cash_flow")
        if free_cash_flow and market_cap and market_cap > 0:
            calculated["fcf_yield"] = (free_cash_flow / market_cap) * 100
    
    def _calculate_growth_metrics(self, extracted: dict, calculated: dict) -> None:
        """Calculate growth metrics."""
        revenue_data = extracted.get("revenue")
        if isinstance(revenue_data, dict):
            revenue_current = revenue_data.get("current")
            revenue_previous = revenue_data.get("previous")
            if revenue_current and revenue_previous and revenue_previous > 0:
                calculated["revenue_growth_pct"] = ((revenue_current - revenue_previous) / revenue_previous) * 100
        
        net_income = extracted.get("net_income")
        net_income_previous = extracted.get("net_income_previous")
        if net_income and net_income_previous and net_income_previous > 0:
            calculated["net_income_growth_pct"] = ((net_income - net_income_previous) / net_income_previous) * 100
    
    def _calculate_health_metrics(self, extracted: dict, calculated: dict, stock_price: float) -> None:
        """Calculate financial health metrics."""
        net_income = extracted.get("net_income")
        shareholders_equity = extracted.get("shareholders_equity")
        if net_income and shareholders_equity and shareholders_equity > 0:
            calculated["roe"] = (net_income / shareholders_equity) * 100
        
        total_assets = extracted.get("total_assets")
        if net_income and total_assets and total_assets > 0:
            calculated["roa"] = (net_income / total_assets) * 100
        
        total_debt = extracted.get("total_debt")
        if total_debt and shareholders_equity and shareholders_equity > 0:
            calculated["debt_to_equity"] = total_debt / shareholders_equity
        
        current_assets = extracted.get("current_assets")
        current_liabilities = extracted.get("current_liabilities")
        if current_assets and current_liabilities and current_liabilities > 0:
            calculated["current_ratio"] = current_assets / current_liabilities
        
        if current_assets and current_liabilities:
            calculated["working_capital"] = current_assets - current_liabilities
        
        operating_income = extracted.get("operating_income")
        revenue_data = extracted.get("revenue")
        if isinstance(revenue_data, dict):
            revenue = revenue_data.get("current")
        else:
            revenue = revenue_data
        
        if operating_income and revenue and revenue > 0:
            calculated["operating_margin"] = (operating_income / revenue) * 100
        
        if net_income and revenue and revenue > 0:
            calculated["net_margin"] = (net_income / revenue) * 100
        
        capex = extracted.get("capital_expenditures")
        if capex and revenue and revenue > 0:
            calculated["capex_pct_revenue"] = (abs(capex) / revenue) * 100
        
        dividends_paid = extracted.get("dividends_paid")
        if dividends_paid and net_income and net_income > 0:
            calculated["payout_ratio"] = (dividends_paid / net_income) * 100
        
        free_cash_flow = extracted.get("free_cash_flow")
        if dividends_paid and free_cash_flow and free_cash_flow != 0:
            calculated["fcf_coverage"] = free_cash_flow / abs(dividends_paid)
        
        cash = extracted.get("cash")
        shares_outstanding = extracted.get("shares_outstanding") or calculated.get("shares_outstanding")
        if cash and shares_outstanding and shares_outstanding > 0:
            calculated["cash_per_share"] = cash / shares_outstanding
        
        if total_debt and total_assets and total_assets > 0:
            calculated["debt_to_assets"] = total_debt / total_assets
        
        accounts_receivable = extracted.get("accounts_receivable")
        if accounts_receivable is not None and current_liabilities and current_liabilities > 0:
            quick_assets = cash + accounts_receivable if cash else accounts_receivable
            calculated["quick_ratio"] = quick_assets / current_liabilities
        
        cogs = extracted.get("cogs")
        if cogs is not None and revenue and revenue > 0:
            calculated["gross_margin_pct"] = ((revenue - cogs) / revenue) * 100
        
        interest_expense = extracted.get("interest_expense")
        if operating_income and interest_expense and interest_expense > 0:
            calculated["interest_coverage"] = operating_income / interest_expense

