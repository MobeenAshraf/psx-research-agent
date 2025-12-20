"""LLM decision routes."""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from financial.config.user_profile_loader import UserProfileLoader
from financial.config.model_config import ModelConfig
from financial.langgraph.decision_llm_helper import DecisionLLMHelper
from financial.langgraph.api_client import OpenRouterAPIClient
from financial.services.index_membership_service import get_index_service
from routes.technical import get_technical_analysis
from routes.financial import check_latest_report, _get_existing_states


def get_llm_decision(
    symbol: str,
    extraction_model: Optional[str] = "auto",
    analysis_model: Optional[str] = "auto",
    decision_model: Optional[str] = "auto"
) -> Dict[str, Any]:
    """
    Get LLM decision combining user profile, technical analysis, and financial analysis.
    
    Args:
        symbol: Stock symbol
        extraction_model: Model for extraction (used to find cached financial analysis)
        analysis_model: Model for analysis (used to find cached financial analysis)
        decision_model: Model for decision-making
        
    Returns:
        Dictionary with decision, confidence, reasoning, etc.
    """
    try:
        symbol_upper = symbol.upper()
        
        # Load user profile
        try:
            user_profile = UserProfileLoader.load_profile()
        except (FileNotFoundError, ValueError) as e:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Failed to load user profile: {str(e)}"
            }
        
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
        
        # Get final report from states (use normalized models to match the cached result)
        normalized_extraction = ModelConfig.normalize_model_name(extraction_model, is_extraction=True)
        normalized_analysis = ModelConfig.normalize_model_name(analysis_model, is_extraction=False)
        states = _get_existing_states(
            symbol_upper,
            extraction_model=normalized_extraction,
            analysis_model=normalized_analysis
        )
        final_state = states.get("99_final", {})
        financial_report = final_state.get("final_report", "")
        
        if not financial_report:
            financial_report = financial_result.get("result", "")
        
        if not financial_report:
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": "Financial analysis report not available"
            }
        
        # Build prompt summaries
        user_profile_summary = json.dumps(user_profile, indent=2)
        
        technical_summary = f"""
Symbol: {symbol_upper}
Recommendation: {technical_analysis.get('recommendation', 'N/A')}
Confidence: {technical_analysis.get('confidence', 0):.2f}
Key Indicators: {json.dumps(technical_analysis.get('indicators', {}), indent=2)}
Reasoning: {json.dumps(technical_analysis.get('reasoning', []), indent=2)}
"""
        
        financial_summary = financial_report[:2000] if len(financial_report) > 2000 else financial_report
        
        # Get index membership data
        index_service = get_index_service()
        index_membership = index_service.get_index_membership(symbol_upper)
        index_membership_summary = json.dumps(index_membership, indent=2)
        
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
        
        if not schema_path.exists():
            return {
                "symbol": symbol_upper,
                "status": "error",
                "error": f"Decision schema file not found: {schema_path}"
            }
        
        system_prompt_template = decision_prompt_path.read_text(encoding='utf-8')
        schema_content = schema_path.read_text(encoding='utf-8')
        
        # Replace placeholders in prompt
        system_prompt = system_prompt_template.replace("{SCHEMA_PLACEHOLDER}", schema_content)
        system_prompt = system_prompt.replace("{USER_PROFILE_PLACEHOLDER}", user_profile_summary)
        system_prompt = system_prompt.replace("{TECHNICAL_ANALYSIS_SUMMARY_PLACEHOLDER}", technical_summary)
        system_prompt = system_prompt.replace("{FINANCIAL_ANALYSIS_SUMMARY_PLACEHOLDER}", financial_summary)
        system_prompt = system_prompt.replace("{INDEX_MEMBERSHIP_PLACEHOLDER}", index_membership_summary)
        
        user_prompt = f"Analyze stock {symbol_upper} and provide your investment decision."
        
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
            "raw_response": json.dumps(decision_result, indent=2),
            "token_usage": token_usage
        }
        
    except Exception as exc:
        return {
            "symbol": symbol.upper(),
            "status": "error",
            "error": str(exc)
        }

