from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from financial.langgraph.analyzer import LangGraphAnalyzer
from financial.langgraph.workflow_steps.calculate_step import calculate_metrics
from financial.langgraph.workflow_steps.format_step import FormatStep
from financial.pdf_exceptions import LLMAnalysisError
from financial.services.shariah_source import get_psx_shariah_status
from financial.statement_values import normalize_statement
from financial.validators.financial_validator import FinancialMetricsValidator
from technical.analyzer import TechnicalAnalyzer
from technical.backtest import replay
from technical.indicators.macd_calculator import MACDCalculator
from technical.indicators.rsi_calculator import RSICalculator
from technical.price_repository import MARKET_TZ, WebPriceRepository
from technical.recommendation.macd_strategy import MACDStrategy
from technical.recommendation_engine import RecommendationEngine


def statement(**overrides):
    return {
        "company_name": "Fixture",
        "currency": "PKR",
        "period_end": "2026-09-30",
        "period_months": 12,
        "reporting_scope": "standalone",
        "monetary_scale": 1000,
        "revenue": {"current": 1000, "previous": 500},
        "cogs": -600,
        "net_income": 200,
        "net_income_previous": 250,
        "total_debt": 0,
        "cash": 50,
        "ebitda": 250,
        "operating_cash_flow": 150,
        "capital_expenditures": -150,
        "dividends_paid": 0,
        "shareholders_equity": 400,
        "total_equity": 400,
        "total_assets": 900,
        "total_liabilities": 500,
        "shares_outstanding": 10000,
        "eps": 20,
        **overrides,
    }


def test_statement_scale_sign_and_reported_zeroes():
    normalized = normalize_statement(statement())
    metrics = calculate_metrics(normalized, stock_price=100)
    assert normalized["shares_outstanding"] == 10000
    assert normalized["eps"] == 20
    assert metrics["market_cap"] == 1_000_000
    assert metrics["gross_margin_pct"] == 40
    assert metrics["payout_ratio"] == 0
    assert metrics["fcf_yield"] == 0
    assert metrics["debt_to_equity"] == 0
    assert metrics["ev_ebitda"] == 3.8
    assert "fcf_coverage" not in metrics
    assert calculate_metrics(normalize_statement(statement(net_income=0)))["net_income_growth_pct"] == -100


def test_trailing_ratios_need_trailing_flows_and_reported_shares():
    normalized = normalize_statement(statement(period_months=3, shares_outstanding=None))
    metrics = calculate_metrics(normalized, stock_price=100)
    assert "pe_ratio" not in metrics
    assert "market_cap" not in metrics
    assert "ev_ebitda" not in metrics
    enriched = normalize_statement(statement(period_months=3, ttm_eps=25))
    assert calculate_metrics(enriched, stock_price=100)["pe_ratio"] == 4
    assert "pe_ratio" not in calculate_metrics(normalize_statement(statement(currency="USD")), 100)


def test_balance_sheet_uses_total_equity_for_consolidated_statements():
    data = normalize_statement(statement(reporting_scope="consolidated", shareholders_equity=350))
    validator = FinancialMetricsValidator()
    assert validator.validate_all(data)["is_valid"]
    assert calculate_metrics(data, 100)["ev_ebitda"] == 4
    assert not validator.validate_all({**data, "total_liabilities": 400_000})["is_valid"]


def test_cash_flow_reconciliation_includes_lucky_cement_translation_effect():
    data = normalize_statement(statement(
        beginning_cash=176793432, net_change_cash=20466240,
        cash_fx_effect=-219029, ending_cash=197040643,
    ))
    validator = FinancialMetricsValidator()
    assert validator.validate_cash_flow_reconciliation(data)
    assert not validator.validate_cash_flow_reconciliation({**data, "cash_fx_effect": None})


def test_report_renders_calculations_instead_of_model_numbers():
    data = normalize_statement(statement())
    state = {
        "errors": [],
        "extracted_data": data,
        "calculated_metrics": calculate_metrics(data, 100),
        "analysis_results": {
            "valuation_metrics": {"pe_ratio": 12345},
            "dividend_analysis": {"payout_ratio": 12345},
        },
    }
    report = FormatStep(Mock()).execute(state)["final_report"]
    assert "- Trailing P/E: 5.00x" in report
    assert "- Payout Ratio: 0.00%" in report
    assert "12345" not in report


def test_workflow_stops_before_llm_analysis_on_failed_reconciliation():
    analyzer = LangGraphAnalyzer(api_key="test-key")
    with (
        patch.object(analyzer.state_manager, "setup_state_dir"),
        patch.object(analyzer.llm_helper, "call_llm_with_pdf", return_value=(
            statement(total_liabilities=200), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )),
        patch.object(analyzer.llm_helper, "call_llm_with_json_response") as analyze,
    ):
        with pytest.raises(LLMAnalysisError, match="Balance sheet does not balance"):
            analyzer.analyze(pdf_text="", pdf_path="fixture.pdf")
    analyze.assert_not_called()


def test_psx_list_is_source_information_and_handles_unavailable_source():
    response = Mock(content=b"""
        <table><thead><tr><th>Symbol</th><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/company/INDU">INDU</a></td><td>Indus</td></tr></tbody></table>
        <table><thead><tr><th>Symbol</th><th>Name</th></tr></thead>
        <tbody><tr><td><a href="/sukuk/X">X</a></td><td>Sukuk</td></tr></tbody></table>
    """)
    with patch("financial.services.shariah_source.requests.get", return_value=response):
        assert get_psx_shariah_status("INDU")["status"] == "listed"
        assert get_psx_shariah_status("X")["status"] == "not_listed"
        response.content = b"<html>Unavailable</html>"
        assert get_psx_shariah_status("INDU")["status"] == "unavailable"


def test_price_feed_keeps_zero_volume_and_omits_unreported_range():
    repository = WebPriceRepository()
    now = datetime.now(MARKET_TZ).timestamp()
    repository.session.get = Mock()
    repository.session.get.return_value.headers = {}
    repository.session.get.return_value.json.return_value = {"data": [[now, 108, 0, 103]]}
    bar = repository.get_historical_prices("TEST")[0]
    assert bar["volume"] == 0 and bar["open"] == 103
    assert "high" not in bar and "low" not in bar
    history = [
        {**bar, "date": bar["date"] - timedelta(days=day)}
        for day in reversed(range(60))
    ]
    analyzer = TechnicalAnalyzer()
    indicators = analyzer.calculate_indicators(history)
    assert indicators["rsi"] == 50
    assert "trend" in indicators
    assert "atr" not in indicators and "fibonacci" not in indicators
    assert analyzer.get_candlestick_patterns(history) == []


def test_technical_conflict_is_independent_of_strategy_order():
    engine = RecommendationEngine()
    indicators = {"rsi": 20, "macd": 1, "macd_signal": 2}
    assert engine.generate_recommendation(indicators, {}, [])[0] == "Hold"
    engine.strategies.reverse()
    assert engine.generate_recommendation(indicators, {}, [])[0] == "Hold"
    assert MACDStrategy().evaluate({"macd": 0, "macd_signal": 1}, {})[0] == "Sell"
    assert MACDStrategy().evaluate({"macd": 1, "macd_signal": 1}, {})[0] == "Hold"


def test_rsi_and_macd_crossing_handle_edge_cases():
    assert RSICalculator().calculate(pd.Series([1] * 15)) == 50
    assert RSICalculator().calculate(pd.Series(range(15))) == 100
    assert MACDCalculator().calculate(pd.Series([100] * 40 + [110]))["crossover"] == "bullish"
    assert MACDCalculator().calculate(pd.Series([100] * 40 + [110, 111]))["crossover"] is None


def test_backtest_executes_on_next_session_and_applies_costs():
    start = date(2025, 1, 1)
    history = [
        {"date": start + timedelta(days=index), "close": price, "volume": 1000}
        for index, price in enumerate([100] * 50 + [103, 108, 110])
    ]
    with patch.object(RecommendationEngine, "generate_recommendation", return_value=("Buy", 0.6, [])):
        report = replay(history, start=start, cost_bps=100, min_turnover=10_000)
        blocked = replay(history, start=start, cost_bps=100, min_turnover=1_000_000)
    assert report["trades"][0]["signal_date"] == history[49]["date"].isoformat()
    assert report["trades"][0]["execution_date"] == history[50]["date"].isoformat()
    assert report["net_return"] == pytest.approx(110 / (103 * 1.01) - 1)
    assert blocked["trades"] == [] and blocked["trades_skipped_for_liquidity"] == 3


def test_cached_report_must_match_source_and_latest_run(tmp_path, monkeypatch):
    from financial.langgraph import state_manager
    from financial.repositories.file_result_repository import FileResultRepository
    from state_monitor import read_states

    monkeypatch.setattr(state_manager, "DEFAULT_RESULTS_DIRECTORY", tmp_path)
    manager = state_manager.StateManager()
    repository = FileResultRepository(base_dir=tmp_path)
    manager.setup_state_dir("TEST", "extract", "analyze")
    data = {"report_url": "https://example.org/report.pdf", "validation_results": {"is_valid": True}}
    manager.save_state(data, "00_initial")
    manager.save_state(data, "99_final")
    repository.save_result("TEST", "statement", "report", "extract", "analyze")

    assert repository.has_valid_analysis("TEST", "statement", data["report_url"], "extract", "analyze")
    assert not repository.has_valid_analysis("TEST", "statement", "https://example.org/new.pdf", "extract", "analyze")

    manager.setup_state_dir("TEST", "extract", "analyze")
    manager.save_state(data, "00_initial")
    assert "99_final" not in read_states(tmp_path / "TEST" / "extract_analyze" / "states")
    assert not repository.has_valid_analysis("TEST", "statement", data["report_url"], "extract", "analyze")


def test_decision_reprices_validated_facts_and_displays_psx_status_separately(monkeypatch):
    from routes import decision

    data = normalize_statement(statement())
    final = {
        "extracted_data": data,
        "validation_results": {"is_valid": True, "warnings": []},
        "calculated_metrics": {"pe_ratio": 999},
        "final_report": "Rendered report with potentially stale pricing",
    }
    quote = {"current_price": 180, "price_as_of": "2026-11-20"}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(decision, "get_technical_analysis", Mock(return_value={"indicators": quote}))
    monkeypatch.setattr(decision, "check_latest_report", Mock(return_value={
        "status": "exists", "states": {"99_final": final},
    }))
    monkeypatch.setattr(decision, "get_index_service", Mock())
    decision.get_index_service.return_value.get_index_membership.return_value = {}
    psx_status = {"status": "not_listed", "checked_on": "2026-11-20"}
    monkeypatch.setattr(decision, "get_psx_shariah_status", Mock(return_value=psx_status))

    with patch.object(decision.DecisionLLMHelper, "call_decision_llm", return_value=(
        {"decision": "BUY", "summary": "Fixture decision"}, {},
    )) as llm:
        response = decision.get_llm_decision("TEST", user_profile={"halal_only": True})
    assert response["status"] == "success"
    assert response["decision"] == "BUY"
    assert response["psx_shariah"] == psx_status
    prompt = llm.call_args.kwargs["system_prompt"]
    assert '"pe_ratio": 9.0' in prompt
    assert "potentially stale pricing" not in prompt
    assert '"not_listed"' not in prompt
