"""OpenRouter API client for LangGraph workflow."""

from math import isfinite

import requests
from typing import Dict, Optional, List, Tuple
from financial.pdf_exceptions import LLMAnalysisError


def read_token_usage(result: dict) -> Dict[str, int | float]:
    usage = result.get("usage") or {}
    tokens = {key: usage.get(key) or 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    cost = usage.get("cost")
    if type(cost) in (int, float) and isfinite(cost) and cost >= 0:
        tokens["cost_usd"] = cost
    return tokens


class OpenRouterAPIClient:
    """OpenRouter API client for LLM calls."""
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        response_format: Optional[Dict[str, str]] = None
    ) -> Tuple[str, Dict[str, int | float]]:
        """Call OpenRouter API. Returns (content, token_usage)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 8000,
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise LLMAnalysisError("No response from OpenRouter API")
            
            content = result["choices"][0]["message"]["content"]
            
            return content, read_token_usage(result)
        except requests.RequestException as e:
            raise LLMAnalysisError(f"OpenRouter API error: {str(e)}")
        except (KeyError, IndexError) as e:
            raise LLMAnalysisError(f"Invalid response format: {str(e)}")
    
    def call_with_pdf(
        self,
        pdf_path: str,
        messages: List[Dict],
        model: str,
        response_format: Optional[Dict[str, str]] = None
    ) -> Tuple[str, Dict[str, int | float]]:
        """Call OpenRouter API with PDF. Delegates to PDFAPIClient."""
        from financial.langgraph.api.pdf_client import PDFAPIClient
        pdf_client = PDFAPIClient(self.api_key)
        return pdf_client.call_with_pdf(pdf_path, messages, model, response_format)

