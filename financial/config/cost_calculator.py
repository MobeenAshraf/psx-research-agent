"""Cost calculation utility for LLM token usage."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_PRICING_CACHE = None


def _load_pricing() -> Dict[str, Dict[str, float]]:
    """Load pricing configuration from JSON file."""
    global _PRICING_CACHE
    
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE
    
    pricing_file = Path(__file__).parent / "model_pricing.json"
    
    try:
        with open(pricing_file, "r", encoding="utf-8") as f:
            _PRICING_CACHE = json.load(f)
        return _PRICING_CACHE
    except FileNotFoundError:
        logger.warning(f"Pricing file not found: {pricing_file}")
        _PRICING_CACHE = {}
        return _PRICING_CACHE
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse pricing file: {e}")
        _PRICING_CACHE = {}
        return _PRICING_CACHE


def get_model_pricing(model_name: str) -> Optional[Dict[str, float]]:
    """
    Get pricing rates for a model.
    
    Args:
        model_name: Model identifier (e.g., "openai/gpt-4o")
        
    Returns:
        Dictionary with "prompt_tokens_per_million" and "completion_tokens_per_million",
        or None if model not found
    """
    pricing = _load_pricing()
    return pricing.get(model_name)


def calculate_cost(token_usage: Dict[str, int], model_name: str) -> float:
    """
    Calculate cost in USD for token usage.
    
    Args:
        token_usage: Dictionary with "prompt_tokens", "completion_tokens", "total_tokens"
        model_name: Model identifier (e.g., "openai/gpt-4o")
        
    Returns:
        Cost in USD, or 0.0 if pricing not available
    """
    if not token_usage:
        return 0.0
    
    pricing = get_model_pricing(model_name)
    if not pricing:
        logger.warning(f"No pricing found for model: {model_name}")
        return 0.0
    
    prompt_tokens = token_usage.get("prompt_tokens", 0)
    completion_tokens = token_usage.get("completion_tokens", 0)
    
    prompt_price_per_million = pricing.get("prompt_tokens_per_million", 0.0)
    completion_price_per_million = pricing.get("completion_tokens_per_million", 0.0)
    
    prompt_cost = (prompt_tokens / 1_000_000) * prompt_price_per_million
    completion_cost = (completion_tokens / 1_000_000) * completion_price_per_million
    
    total_cost = prompt_cost + completion_cost
    
    return round(total_cost, 6)

