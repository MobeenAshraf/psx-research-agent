"""OpenRouter API client for LangGraph workflow."""

import requests
from typing import Dict, Optional, List, Tuple
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
    ) -> Tuple[str, Dict[str, int]]:
        """Call OpenRouter API. Returns (content, token_usage)."""
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
            
            content = result["choices"][0]["message"]["content"]
            
            token_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
            
            if "usage" in result:
                usage = result["usage"]
                token_usage["prompt_tokens"] = usage.get("prompt_tokens", 0)
                token_usage["completion_tokens"] = usage.get("completion_tokens", 0)
                token_usage["total_tokens"] = usage.get("total_tokens", 0)
            
            return content, token_usage
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
    ) -> Tuple[str, Dict[str, int]]:
        """Call OpenRouter API with PDF. Delegates to PDFAPIClient."""
        from financial.langgraph.api.pdf_client import PDFAPIClient
        pdf_client = PDFAPIClient(self.api_key)
        return pdf_client.call_with_pdf(pdf_path, messages, model, response_format)

