"""LLM helper for shared LLM call logic."""

import json
from typing import Dict, Any, Optional
try:
    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
except ImportError:
    from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from psx_analysis.financial_analysis.pdf_exceptions import LLMAnalysisError
from psx_analysis.financial_analysis.langgraph.json_parser import JSONParser
from psx_analysis.financial_analysis.langgraph.api_client import OpenRouterAPIClient


class LLMHelper:
    """Helper class for LLM calls with JSON response format."""
    
    def __init__(self, api_client: OpenRouterAPIClient, json_parser: JSONParser):
        self.api_client = api_client
        self.json_parser = json_parser
    
    def call_llm_with_json_response(
        self,
        system_prompt_content: str,
        user_prompt_content: str,
        model: str,
        state_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with JSON response format, handling prompt creation, API call, and parsing.
        
        Args:
            system_prompt_content: System prompt content
            user_prompt_content: User prompt content (can contain template variables)
            model: Model name to use
            state_context: Optional context dict for template formatting
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            LLMAnalysisError: If API call or parsing fails
        """
        response = None
        try:
            system_prompt = SystemMessagePromptTemplate.from_template(system_prompt_content)
            user_prompt = HumanMessagePromptTemplate.from_template(user_prompt_content)
            
            chat_prompt = ChatPromptTemplate.from_messages([system_prompt, user_prompt])
            
            if state_context:
                formatted_messages = chat_prompt.format_messages(**state_context)
            else:
                formatted_messages = chat_prompt.format_messages()
            
            messages = []
            for msg in formatted_messages:
                msg_class_name = msg.__class__.__name__
                if 'SystemMessage' in msg_class_name:
                    role = "system"
                elif 'HumanMessage' in msg_class_name:
                    role = "user"
                else:
                    role = "user"
                messages.append({"role": role, "content": msg.content})
            
            response = self.api_client.call(
                messages=messages,
                model=model,
                response_format={"type": "json_object"}
            )
            
            try:
                return self.json_parser.parse_response(response)
            except Exception as parse_err:
                error_details = f"Parse error: {str(parse_err)}\n"
                error_details += f"Response length: {len(response)}\n"
                error_details += f"Response (first 2000 chars): {repr(response[:2000])}\n"
                error_details += f"Response type: {type(response)}"
                print(f"\n[FULL ERROR DETAILS]\n{error_details}", flush=True)
                raise LLMAnalysisError(error_details) from parse_err
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON: {e.msg} (at position {e.pos})"
            if response:
                error_msg += f"\nResponse (first 2000 chars): {repr(response[:2000])}"
                error_msg += f"\nResponse length: {len(response)}"
                error_msg += f"\nResponse around error: {repr(response[max(0, e.pos-100):e.pos+100])}"
            raise LLMAnalysisError(error_msg) from e
        except Exception as e:
            import traceback
            error_msg = f"LLM call error: {type(e).__name__}: {str(e)}"
            if response:
                error_msg += f"\nResponse (first 2000 chars): {repr(response[:2000])}"
                error_msg += f"\nResponse length: {len(response)}"
            error_msg += f"\nTraceback: {traceback.format_exc()}"
            raise LLMAnalysisError(error_msg) from e

