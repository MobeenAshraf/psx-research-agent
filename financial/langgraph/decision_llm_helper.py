"""LLM helper for decision-making prompts."""

import json
from typing import Dict, Any, Tuple
from financial.langgraph.api_client import OpenRouterAPIClient
from financial.pdf_exceptions import LLMAnalysisError


class DecisionLLMHelper:
    """Helper class for LLM decision calls."""
    
    def __init__(self, api_client: OpenRouterAPIClient):
        self.api_client = api_client
    
    def call_decision_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Call LLM for decision-making with JSON response format.
        
        Args:
            system_prompt: System prompt content
            user_prompt: User prompt content
            model: Model name to use
            
        Returns:
            Tuple of (parsed_json_response, token_usage) where token_usage contains:
            - prompt_tokens: Number of tokens in the prompt
            - completion_tokens: Number of tokens in the completion
            - total_tokens: Total tokens used
            
        Raises:
            LLMAnalysisError: If API call or parsing fails
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response, token_usage = self.api_client.call(
                messages=messages,
                model=model,
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_response = json.loads(response)
                return parsed_response, token_usage
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON response: {e.msg} (at position {e.pos})"
                error_msg += f"\nResponse (first 2000 chars): {repr(response[:2000])}"
                error_msg += f"\nResponse length: {len(response)}"
                raise LLMAnalysisError(error_msg) from e
                
        except Exception as e:
            error_msg = f"Decision LLM call error: {type(e).__name__}: {str(e)}"
            raise LLMAnalysisError(error_msg) from e

