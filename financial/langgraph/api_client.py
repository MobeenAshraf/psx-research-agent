"""OpenRouter API client for LangGraph workflow."""

import base64
import requests
from pathlib import Path
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
        """Call OpenRouter API with PDF. Returns (content, token_usage)."""
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                raise LLMAnalysisError(f"PDF file not found: {pdf_path}")
            
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
            
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            data_url = f"data:application/pdf;base64,{base64_pdf}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            modified_messages = []
            for msg in messages:
                msg_copy = msg.copy()
                content = msg_copy.get("content", "")
                
                if isinstance(content, str):
                    msg_copy["content"] = [
                        {
                            "type": "text",
                            "text": content
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": pdf_file.name,
                                "file_data": data_url
                            }
                        }
                    ]
                elif isinstance(content, list):
                    content_copy = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            content_copy.append(item)
                        elif isinstance(item, str):
                            content_copy.append({"type": "text", "text": item})
                        else:
                            content_copy.append(item)
                    content_copy.append({
                        "type": "file",
                        "file": {
                            "filename": pdf_file.name,
                            "file_data": data_url
                        }
                    })
                    msg_copy["content"] = content_copy
                else:
                    msg_copy["content"] = [
                        {
                            "type": "text",
                            "text": str(content)
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": pdf_file.name,
                                "file_data": data_url
                            }
                        }
                    ]
                modified_messages.append(msg_copy)
            
            payload = {
                "model": model,
                "messages": modified_messages,
                "temperature": 0,
                "max_tokens": 16000,
            }
            
            if response_format:
                payload["response_format"] = response_format
            
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
            
            choice = result["choices"][0]
            content = choice["message"].get("content", "")
            finish_reason = choice.get("finish_reason", "")
            
            if finish_reason == "length":
                raise LLMAnalysisError(
                    f"Response truncated due to max_tokens limit. "
                    f"Response length: {len(content)} characters. "
                    f"Consider increasing max_tokens or simplifying the extraction schema."
                )
            
            if not content:
                raise LLMAnalysisError(
                    f"Empty response from API. Finish reason: {finish_reason}. "
                    f"Check if model supports response_format or if prompt is too complex."
                )
            
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
        except FileNotFoundError as e:
            raise LLMAnalysisError(f"PDF file not found: {str(e)}")
        except requests.RequestException as e:
            error_msg = f"OpenRouter API error with PDF: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    if "error" in error_detail:
                        error_msg += f" - {error_detail['error']}"
                except:
                    error_msg += f" - Response: {e.response.text[:200]}"
            raise LLMAnalysisError(error_msg) from e
        except (KeyError, IndexError) as e:
            raise LLMAnalysisError(f"Invalid response format: {str(e)}")

