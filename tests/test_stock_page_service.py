"""Tests for StockPageService - webpage verification, data extraction, and validation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from financial.services.stock_page_service import (
    StockPageService,
    StockPageFinancials,
    get_stock_page_service,
)


class TestStockPageService:
    """Tests for StockPageService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = StockPageService()

    def test_parse_numeric_value_positive(self):
        """Test parsing positive numeric values."""
        assert self.service._parse_numeric_value("1,234,567") == 1234567.0
        assert self.service._parse_numeric_value("123.45") == 123.45
        assert self.service._parse_numeric_value("10") == 10.0

    def test_parse_numeric_value_negative_parentheses(self):
        """Test parsing negative values in parentheses format."""
        assert self.service._parse_numeric_value("(123.45)") == -123.45
        assert self.service._parse_numeric_value("(1,000)") == -1000.0

    def test_parse_numeric_value_percentage(self):
        """Test parsing percentage values."""
        assert self.service._parse_numeric_value("25.5%") == 25.5
        assert self.service._parse_numeric_value("(10.5%)") == -10.5

    def test_parse_numeric_value_empty_or_invalid(self):
        """Test parsing empty or invalid values returns None."""
        assert self.service._parse_numeric_value("") is None
        assert self.service._parse_numeric_value("-") is None
        assert self.service._parse_numeric_value("N/A") is None
        assert self.service._parse_numeric_value("n/a") is None

    def test_normalize_metric_name_sales(self):
        """Test normalizing sales metric name."""
        assert self.service._normalize_metric_name("Sales") == "sales"
        assert self.service._normalize_metric_name("Total Income") == "sales"
        assert self.service._normalize_metric_name("SALES") == "sales"

    def test_normalize_metric_name_profit(self):
        """Test normalizing profit metric name."""
        assert self.service._normalize_metric_name("Profit after Taxation") == "profit_after_tax"
        assert self.service._normalize_metric_name("Net Income") == "profit_after_tax"

    def test_normalize_metric_name_eps(self):
        """Test normalizing EPS metric name."""
        assert self.service._normalize_metric_name("EPS") == "eps"
        assert self.service._normalize_metric_name("Earnings Per Share") == "eps"

    def test_normalize_metric_name_unknown(self):
        """Test normalizing unknown metric returns None."""
        assert self.service._normalize_metric_name("Unknown Metric") is None
        assert self.service._normalize_metric_name("Random Text") is None

    def test_normalize_ratio_name(self):
        """Test normalizing ratio names."""
        assert self.service._normalize_ratio_name("Net Profit Margin (%)") == "net_profit_margin"
        assert self.service._normalize_ratio_name("EPS Growth (%)") == "eps_growth"
        assert self.service._normalize_ratio_name("PEG") == "peg"
        assert self.service._normalize_ratio_name("Gross Profit Margin (%)") == "gross_profit_margin"

    def test_normalize_ratio_name_unknown(self):
        """Test normalizing unknown ratio returns None."""
        assert self.service._normalize_ratio_name("Unknown Ratio") is None


class TestStockPageFinancialsValidation:
    """Tests for data validation in StockPageFinancials."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = StockPageService()

    def test_validate_data_minimum_years(self):
        """Test validation requires minimum annual years."""
        result = StockPageFinancials(
            symbol="TEST",
            annual_data={
                "2024": {"sales": 1000000, "profit_after_tax": 100000, "eps": 10.0}
            },
        )

        is_valid = self.service._validate_data(result)
        assert not is_valid
        assert any("Insufficient annual data" in e for e in result.validation_errors)

    def test_validate_data_sufficient_years(self):
        """Test validation passes with sufficient years."""
        result = StockPageFinancials(
            symbol="TEST",
            annual_data={
                "2024": {"sales": 1000000, "profit_after_tax": 100000, "eps": 10.0},
                "2023": {"sales": 900000, "profit_after_tax": 90000, "eps": 9.0},
            },
        )

        is_valid = self.service._validate_data(result)
        assert is_valid

    def test_validate_metric_ranges_negative_sales(self):
        """Test validation catches negative sales."""
        result = StockPageFinancials(
            symbol="TEST",
            annual_data={
                "2024": {"sales": -1000000, "profit_after_tax": 100000, "eps": 10.0},
                "2023": {"sales": 900000, "profit_after_tax": 90000, "eps": 9.0},
            },
        )

        is_valid = self.service._validate_metric_ranges(result)
        assert not is_valid
        assert any("Invalid negative sales" in e for e in result.validation_errors)

    def test_validate_metric_ranges_extreme_npm(self):
        """Test validation catches extreme net profit margin."""
        result = StockPageFinancials(
            symbol="TEST",
            annual_data={
                "2024": {"sales": 1000000, "profit_after_tax": 100000, "eps": 10.0},
                "2023": {"sales": 900000, "profit_after_tax": 90000, "eps": 9.0},
            },
            ratios={
                "2024": {"net_profit_margin": 150.0},
                "2023": {"net_profit_margin": 10.0},
            },
        )

        is_valid = self.service._validate_metric_ranges(result)
        assert not is_valid
        assert any("Net profit margin out of range" in e for e in result.validation_errors)


class TestStockPageServiceFetch:
    """Tests for StockPageService fetch operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = StockPageService()

    @patch.object(StockPageService, "_fetch_page")
    def test_fetch_stock_financials_page_not_found(self, mock_fetch):
        """Test returns None when page not found."""
        mock_fetch.return_value = None

        result = self.service.fetch_stock_financials("INVALID")

        assert result is None

    @patch.object(StockPageService, "_fetch_page")
    def test_fetch_stock_financials_invalid_structure(self, mock_fetch):
        """Test returns None when page structure is invalid."""
        mock_fetch.return_value = "<html><body>No tables here</body></html>"

        result = self.service.fetch_stock_financials("TEST")

        assert result is None


class TestGetLatestData:
    """Tests for getting latest annual/quarterly data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = StockPageService()

    def test_get_latest_annual_data(self):
        """Test getting latest annual data."""
        financials = StockPageFinancials(
            symbol="TEST",
            annual_data={
                "2024": {"sales": 1000000, "eps": 10.0},
                "2023": {"sales": 900000, "eps": 9.0},
                "2022": {"sales": 800000, "eps": 8.0},
            },
            ratios={
                "2024": {"net_profit_margin": 15.0, "peg": 1.2},
                "2023": {"net_profit_margin": 12.0, "peg": 1.5},
            },
            is_valid=True,
        )

        result = self.service.get_latest_annual_data(financials)

        assert result is not None
        assert result["year"] == "2024"
        assert result["metrics"]["sales"] == 1000000
        assert result["metrics"]["eps"] == 10.0
        assert result["ratios"]["net_profit_margin"] == 15.0
        assert result["ratios"]["peg"] == 1.2

    def test_get_latest_annual_data_empty(self):
        """Test returns None when no annual data."""
        financials = StockPageFinancials(symbol="TEST", annual_data={}, is_valid=True)

        result = self.service.get_latest_annual_data(financials)

        assert result is None

    def test_get_latest_quarterly_data(self):
        """Test getting latest quarterly data."""
        financials = StockPageFinancials(
            symbol="TEST",
            quarterly_data={
                "Q1 2025": {"sales": 250000, "eps": 2.5},
                "Q4 2024": {"sales": 240000, "eps": 2.4},
                "Q3 2024": {"sales": 230000, "eps": 2.3},
            },
            is_valid=True,
        )

        result = self.service.get_latest_quarterly_data(financials)

        assert result is not None
        assert result["period"] == "Q1 2025"
        assert result["metrics"]["sales"] == 250000
        assert result["metrics"]["eps"] == 2.5

    def test_get_latest_quarterly_data_empty(self):
        """Test returns None when no quarterly data."""
        financials = StockPageFinancials(symbol="TEST", quarterly_data={}, is_valid=True)

        result = self.service.get_latest_quarterly_data(financials)

        assert result is None


class TestSingletonInstance:
    """Tests for singleton instance."""

    def test_get_stock_page_service_returns_same_instance(self):
        """Test singleton returns same instance."""
        service1 = get_stock_page_service()
        service2 = get_stock_page_service()

        assert service1 is service2

    def test_get_stock_page_service_returns_stock_page_service(self):
        """Test singleton returns StockPageService instance."""
        service = get_stock_page_service()

        assert isinstance(service, StockPageService)


class TestIntegration:
    """Integration tests that make real network requests."""

    @pytest.mark.integration
    def test_fetch_real_stock_luck(self):
        """Test fetching real stock data for LUCK."""
        service = StockPageService()
        result = service.fetch_stock_financials("LUCK")

        if result is not None:
            assert result.symbol == "LUCK"
            assert result.is_valid
            assert len(result.annual_data) >= 2
            assert "sales" in next(iter(result.annual_data.values()))
            assert "eps" in next(iter(result.annual_data.values()))

    @pytest.mark.integration
    def test_fetch_nonexistent_stock(self):
        """Test fetching non-existent stock returns None."""
        service = StockPageService()
        result = service.fetch_stock_financials("ZZZZZZZZZ")

        assert result is None

