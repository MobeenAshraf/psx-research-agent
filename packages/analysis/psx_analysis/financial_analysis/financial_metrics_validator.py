"""Validation logic for financial metrics and cross-statement consistency."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    severity: str  # 'error' or 'warning'


class FinancialMetricsValidator:
    """Validate financial metrics and cross-statement consistency."""
    
    CRITICAL_METRICS = [
        'revenue',
        'net_income',
        'total_assets',
        'total_liabilities',
        'shareholders_equity',
        'operating_cash_flow',
        'free_cash_flow',
    ]
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
    
    def validate_balance_sheet(self, data: Dict[str, Any]) -> bool:
        """
        Validate that balance sheet balances: Assets = Liabilities + Equity.
        
        Args:
            data: Extracted financial data
            
        Returns:
            True if balanced, False otherwise
        """
        total_assets = data.get('total_assets')
        total_liabilities = data.get('total_liabilities')
        shareholders_equity = data.get('shareholders_equity')
        
        if None in (total_assets, total_liabilities, shareholders_equity):
            self.errors.append(ValidationError(
                field='balance_sheet',
                message='Missing required balance sheet components',
                severity='error'
            ))
            return False
        
        calculated_equity = total_assets - total_liabilities
        difference = abs(shareholders_equity - calculated_equity)
        tolerance = total_assets * 0.01  # 1% tolerance
        
        if difference > tolerance:
            self.errors.append(ValidationError(
                field='balance_sheet',
                message=f'Balance sheet does not balance. Assets ({total_assets}) != Liabilities ({total_liabilities}) + Equity ({shareholders_equity}). Difference: {difference}',
                severity='error'
            ))
            return False
        
        return True
    
    def validate_cash_flow_reconciliation(self, data: Dict[str, Any]) -> bool:
        """
        Validate cash flow reconciliation: Beginning Cash + Net Change = Ending Cash.
        
        Args:
            data: Extracted financial data
            
        Returns:
            True if reconciled, False otherwise
        """
        beginning_cash = data.get('beginning_cash')
        net_change_cash = data.get('net_change_cash')
        ending_cash = data.get('ending_cash')
        
        if None in (beginning_cash, net_change_cash, ending_cash):
            self.warnings.append(ValidationError(
                field='cash_flow',
                message='Missing cash flow components for reconciliation',
                severity='warning'
            ))
            return True  # Not critical, just warn
        
        calculated_ending = beginning_cash + net_change_cash
        difference = abs(ending_cash - calculated_ending)
        tolerance = abs(beginning_cash) * 0.01 if beginning_cash != 0 else 1000
        
        if difference > tolerance:
            self.errors.append(ValidationError(
                field='cash_flow',
                message=f'Cash flow does not reconcile. Beginning ({beginning_cash}) + Net Change ({net_change_cash}) != Ending ({ending_cash}). Difference: {difference}',
                severity='error'
            ))
            return False
        
        return True
    
    def validate_net_income_consistency(self, data: Dict[str, Any]) -> bool:
        """
        Validate that Net Income is consistent across Income Statement and Cash Flow Statement.
        
        Args:
            data: Extracted financial data
            
        Returns:
            True if consistent, False otherwise
        """
        income_statement_ni = data.get('net_income')
        cash_flow_ni = data.get('cash_flow_net_income')
        
        if None in (income_statement_ni, cash_flow_ni):
            self.warnings.append(ValidationError(
                field='net_income',
                message='Missing net income from one or both statements',
                severity='warning'
            ))
            return True  # Not critical if one is missing
        
        difference = abs(income_statement_ni - cash_flow_ni)
        tolerance = abs(income_statement_ni) * 0.01 if income_statement_ni != 0 else 1000
        
        if difference > tolerance:
            self.warnings.append(ValidationError(
                field='net_income',
                message=f'Net Income mismatch: Income Statement ({income_statement_ni}) vs Cash Flow ({cash_flow_ni}). Difference: {difference}',
                severity='warning'
            ))
            return True  # Warning, not error (may be due to adjustments)
        
        return True
    
    def validate_critical_metrics(self, data: Dict[str, Any]) -> bool:
        """
        Validate that all critical metrics are present.
        
        Args:
            data: Extracted financial data
            
        Returns:
            True if all critical metrics present, False otherwise
        """
        missing = []
        for metric in self.CRITICAL_METRICS:
            if metric not in data or data[metric] is None:
                missing.append(metric)
        
        if missing:
            self.errors.append(ValidationError(
                field='critical_metrics',
                message=f'Missing critical metrics: {", ".join(missing)}',
                severity='error'
            ))
            return False
        
        return True
    
    def validate_free_cash_flow_calculation(self, data: Dict[str, Any]) -> bool:
        """
        Validate Free Cash Flow calculation: Operating CF - CapEx = FCF.
        
        Args:
            data: Extracted financial data
            
        Returns:
            True if calculation is consistent, False otherwise
        """
        operating_cf = data.get('operating_cash_flow')
        capex = data.get('capital_expenditures')
        free_cash_flow = data.get('free_cash_flow')
        
        if None in (operating_cf, capex, free_cash_flow):
            self.warnings.append(ValidationError(
                field='fcf',
                message='Missing components for FCF validation',
                severity='warning'
            ))
            return True  # Not critical
        
        calculated_fcf = operating_cf - abs(capex)  # CapEx is typically negative
        difference = abs(free_cash_flow - calculated_fcf)
        tolerance = abs(operating_cf) * 0.01 if operating_cf != 0 else 1000
        
        if difference > tolerance:
            self.warnings.append(ValidationError(
                field='fcf',
                message=f'FCF calculation mismatch: Operating CF ({operating_cf}) - CapEx ({capex}) != FCF ({free_cash_flow}). Difference: {difference}',
                severity='warning'
            ))
            return True  # Warning, not error
        
        return True
    
    def validate_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all validation checks.
        
        Args:
            data: Extracted financial data
            
        Returns:
            Dictionary with validation results
        """
        self.errors = []
        self.warnings = []
        
        results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
        }
        
        # Run all validations
        self.validate_critical_metrics(data)
        self.validate_balance_sheet(data)
        self.validate_cash_flow_reconciliation(data)
        self.validate_net_income_consistency(data)
        self.validate_free_cash_flow_calculation(data)
        
        # Collect results
        results['errors'] = [
            {'field': e.field, 'message': e.message}
            for e in self.errors
        ]
        results['warnings'] = [
            {'field': w.field, 'message': w.message}
            for w in self.warnings
        ]
        
        results['is_valid'] = len(self.errors) == 0
        
        return results

