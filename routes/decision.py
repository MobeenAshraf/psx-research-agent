"""LLM decision routes."""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from financial.config.user_profile_loader import UserProfileLoader
from financial.config.model_config import ModelConfig
from financial.prompt_builders import DECISION_RESPONSE_SCHEMA, build_decision_prompts
from financial.config.cost_calculator import calculate_cost
from financial.langgraph.decision_llm_helper import DecisionLLMHelper
from financial.langgraph.api_client import OpenRouterAPIClient
from financial.services.index_membership_service import get_index_service
from routes.technical import get_technical_analysis
from routes.financial import check_latest_report
from financial.statement_calculations import calculate_metrics
from financial.services.shariah_source import get_psx_shariah_status


def get_llm_decision(
    symbol: str,
    extraction_model: Optional[str] = "auto",
    analysis_model: Optional[str] = "auto",
    decision_model: Optional[str] = "auto",
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get LLM decision combining user profile, technical analysis, and financial analysis.
    
    Args:
        symbol: Stock symbol
        extraction_model: Model for extraction (used to find cached financial analysis)
        analysis_model: Model for analysis (used to find cached financial analysis)
        decision_model: Model for decision-making
        user_profile: Optional user profile from frontend (falls back to file if not provided)
        
    Returns:
        Dictionary with decision, confidence, reasoning, etc.
    """
    try:
        symbol_upper = symbol.upper()
        
        # Use provided profile or load from file
        if user_profile:
            profile = user_profile
        else:
            try:
                profile = UserProfileLoader.load_profile()
            except (FileNotFoundError, ValueError) as e:
                return {
                    "symbol": symbol_upper,
                    "status": "error",
                    "error": f"Failed to load user profile: {str(e)}"
                }
        
        user_profile = profile
        
        # Get technical analysis
        try:
            technical_analysis = get_technical_analysis(symbol_upper)
            if technical_analysis.get("status") == "error":
                return {
                    "symbol": symbol_upper,
                    "status": "error",
                    "error": f"Technical analysis failed: {technical_analysis.get('error', 'Unknown error')}"
                }
        except Exception as e:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Failed to get technical analysis: {str(e)}"
            }
        
        # Get financial analysis
        financial_result = check_latest_report(symbol_upper, extraction_model, analysis_model)
        if financial_result.get("status") not in ["exists", "not_found"]:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Financial analysis check failed: {financial_result.get('message', 'Unknown error')}"
            }
        
        if financial_result.get("status") == "not_found":
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "Financial analysis not found. Please run financial analysis first."
            }
        
        final_state = financial_result.get("states", {}).get("99_final", {})
        validation = final_state.get("validation_results") or {}
        extracted = final_state.get("extracted_data") or {}
        if not validation.get("is_valid") or final_state.get("errors") or not extracted:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "Validated financial data is unavailable. Run financial analysis first.",
            }

        indicators = technical_analysis.get("indicators", {})
        price = indicators.get("current_price") if not indicators.get("price_data_stale") else None
        analysis = final_state.get("analysis_results") or {}
        financial_report = {
            "currency": extracted.get("currency"),
            "period_end": extracted.get("period_end"),
            "period_months": extracted.get("period_months"),
            "reporting_scope": extracted.get("reporting_scope"),
            "valuation_price_pkr": price,
            "price_as_of": indicators.get("price_as_of") if price is not None else None,
            "reported": {
                key: extracted.get(key) for key in (
                    "revenue", "net_income", "eps", "cash", "total_debt", "operating_cash_flow",
                    "capital_expenditures", "dividends_paid", "business_model",
                    "dividend_statements", "investor_statements",
                )
            },
            "calculated_metrics": calculate_metrics(extracted, price),
            "validation_warnings": validation.get("warnings", []),
            "analysis_notes": {
                key: analysis.get(key)
                for key in ("investment_growth_areas", "loss_causing_areas", "red_flags")
            },
        }

        index_service = get_index_service()
        index_membership = index_service.get_index_membership(symbol_upper)

        # Load decision prompt and schema
        prompt_dir = Path(__file__).resolve().parents[1] / "financial" / "prompts"
        decision_prompt_path = prompt_dir / "decision_prompt.md"
        schema_path = prompt_dir / "decision_response_schema.json"
        
        if not decision_prompt_path.exists():
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Decision prompt file not found: {decision_prompt_path}"
            }
        
        system_prompt_template = decision_prompt_path.read_text(encoding="utf-8")
        schema_content = schema_path.read_text(encoding="utf-8") if schema_path.exists() else json.dumps(
            DECISION_RESPONSE_SCHEMA, indent=2
        )

        system_prompt, user_prompt = build_decision_prompts(
            system_prompt_template, schema_content, symbol_upper, user_profile,
            technical_analysis, financial_report, index_membership
        )

        # Get decision model
        decision_model_actual = ModelConfig.get_decision_model(decision_model)
        
        # Call decision LLM
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "OPENROUTER_API_KEY environment variable is required"
            }
        
        api_client = OpenRouterAPIClient(api_key)
        decision_helper = DecisionLLMHelper(api_client)
        
        decision_result, token_usage = decision_helper.call_decision_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=decision_model_actual
        )
        
        decision_cost = 0.0
        if token_usage:
            decision_cost = calculate_cost(token_usage, decision_model_actual)
        
        return {
            "symbol": symbol_upper,
            "status": "success",
            "decision": decision_result.get("decision"),
            "confidence": decision_result.get("confidence"),
            "summary": decision_result.get("summary"),
            "reasons": decision_result.get("reasons", []),
            "risk_notes": decision_result.get("risk_notes", []),
            "dividend_analysis": decision_result.get("dividend_analysis"),
            "halal_compliance": decision_result.get("halal_compliance"),
            "psx_shariah": get_psx_shariah_status(symbol_upper),
            "raw_response": json.dumps(decision_result, indent=2),
            "model": decision_model_actual,
            "token_usage": token_usage,
            "cost": decision_cost
        }
        
    except Exception as exc:
        return {
            "symbol": symbol.upper(),
            "status": "error",
            "error": str(exc)
        }

