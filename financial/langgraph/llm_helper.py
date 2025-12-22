"""LLM helper for shared LLM call logic."""

import json
from typing import Dict, Any, Optional, Tuple
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from financial.pdf_exceptions import LLMAnalysisError
from financial.langgraph.json_parser import JSONParser
from financial.langgraph.api_client import OpenRouterAPIClient


class LLMHelper:
    """Helper class for LLM calls with JSON response format."""
    
    def __init__(self, api_client: OpenRouterAPIClient, json_parser: JSONParser):
        self.api_client = api_client
        self.json_parser = json_parser
    
    def _create_prompt_messages(
        self, 
        system_prompt_content: str, 
        user_prompt_content: str,
        state_context: Optional[Dict[str, Any]] = None
    ):
        """Create formatted messages from prompts."""
        system_prompt = SystemMessagePromptTemplate.from_template(system_prompt_content)
        user_prompt = HumanMessagePromptTemplate.from_template(user_prompt_content)
        chat_prompt = ChatPromptTemplate.from_messages([system_prompt, user_prompt])
        
        if state_context:
            return chat_prompt.format_messages(**state_context)
        else:
            return chat_prompt.format_messages()
    
    def _format_messages(self, formatted_messages) -> list:
        """Convert LangChain messages to API format."""
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
        return messages
    
    def _handle_llm_error(
        self, 
        error: Exception, 
        response: Optional[str] = None, 
        error_prefix: str = ""
    ) -> None:
        """Handle LLM call errors with consistent formatting."""
        import traceback
        error_msg = f"{error_prefix}{type(error).__name__}: {str(error)}"
        if response:
            error_msg += f"\nResponse (first 2000 chars): {repr(response[:2000])}"
            error_msg += f"\nResponse length: {len(response)}"
        if isinstance(error, json.JSONDecodeError):
            error_msg += f"\nResponse around error: {repr(response[max(0, error.pos-100):error.pos+100])}"
        error_msg += f"\nTraceback: {traceback.format_exc()}"
        raise LLMAnalysisError(error_msg) from error
    
    def call_llm_with_json_response(
        self,
        system_prompt_content: str,
        user_prompt_content: str,
        model: str,
        state_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Call LLM and return (parsed_response, token_usage). Raises LLMAnalysisError on failure."""
        response = None
        try:
            formatted_messages = self._create_prompt_messages(
                system_prompt_content, user_prompt_content, state_context
            )
            messages = self._format_messages(formatted_messages)
            
            response, token_usage = self.api_client.call(
                messages=messages,
                model=model,
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_response = self.json_parser.parse_response(response)
                return parsed_response, token_usage
            except Exception as parse_err:
                error_details = f"Parse error: {str(parse_err)}\n"
                error_details += f"Response length: {len(response)}\n"
                error_details += f"Response (first 2000 chars): {repr(response[:2000])}\n"
                error_details += f"Response type: {type(response)}"
                print(f"\n[FULL ERROR DETAILS]\n{error_details}", flush=True)
                raise LLMAnalysisError(error_details) from parse_err
            
        except LLMAnalysisError:
            raise
        except json.JSONDecodeError as e:
            self._handle_llm_error(e, response, "Failed to parse JSON: ")
        except Exception as e:
            self._handle_llm_error(e, response, "LLM call error: ")
    
    def call_llm_with_pdf(
        self,
        pdf_path: str,
        system_prompt_content: str,
        user_prompt_content: str,
        model: str,
        state_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Call LLM with PDF and return (parsed_response, token_usage). Raises LLMAnalysisError on failure."""
        response = None
        try:
            formatted_messages = self._create_prompt_messages(
                system_prompt_content, user_prompt_content, state_context
            )
            messages = self._format_messages(formatted_messages)
            
            response, token_usage = self.api_client.call_with_pdf(
                pdf_path=pdf_path,
                messages=messages,
                model=model,
                response_format={"type": "json_object"}
            )
            
            try:
                parsed_response = self.json_parser.parse_response(response)
                return parsed_response, token_usage
            except Exception as parse_err:
                error_details = f"Parse error: {str(parse_err)}\n"
                error_details += f"Response length: {len(response)}\n"
                error_details += f"Response (first 2000 chars): {repr(response[:2000])}\n"
                error_details += f"Response type: {type(response)}"
                print(f"\n[FULL ERROR DETAILS]\n{error_details}", flush=True)
                raise LLMAnalysisError(error_details) from parse_err
            
        except LLMAnalysisError:
            raise
        except json.JSONDecodeError as e:
            self._handle_llm_error(e, response, "Failed to parse JSON: ")
        except Exception as e:
            self._handle_llm_error(e, response, "LLM call with PDF error: ")

