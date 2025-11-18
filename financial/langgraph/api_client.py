"""OpenRouter API client for LangGraph workflow."""

import requests
from typing import Dict, Any, Optional, List
from financial.pdf_exceptions import LLMAnalysisError


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
    ) -> str:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
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
            
            return result["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            raise LLMAnalysisError(f"OpenRouter API error: {str(e)}")
        except (KeyError, IndexError) as e:
            raise LLMAnalysisError(f"Invalid response format: {str(e)}")

