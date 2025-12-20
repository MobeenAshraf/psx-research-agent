"""Multimodal PDF extractor using OpenRouter with Gemini models."""

import base64
import logging
import os
import requests
from pathlib import Path
from typing import Optional

from financial.pdf_extractor import PDFExtractor
from financial.pdf_exceptions import PDFExtractionError

_logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

GEMINI_MODELS = [
    "google/gemini-3-pro-preview",
    "google/gemini-1.5-flash",
    "google/gemini-1.5-pro",
]


class MultimodalPDFExtractor(PDFExtractor):
    """Extract text from PDF using multimodal models via OpenRouter."""
    
    def __init__(self, api_key: Optional[str] = None, extraction_prompt: Optional[str] = None):
        """
        Initialize multimodal PDF extractor.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            extraction_prompt: Custom prompt for extraction (optional)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for multimodal PDF extraction")
        
        self.extraction_prompt = extraction_prompt or """Extract all text content from this PDF document. 
Return the extracted text in a clear, readable format. Preserve the structure and formatting as much as possible.
Include all tables, financial statements, and numerical data."""
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from PDF using multimodal model.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text as string
            
        Raises:
            PDFExtractionError: If extraction fails
        """
        pdf_file = Path(file_path)
        if not pdf_file.exists():
            raise PDFExtractionError(f"PDF file not found: {file_path}")
        
        try:
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
        except Exception as e:
            raise PDFExtractionError(f"Failed to read PDF file: {str(e)}")
        
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        data_url = f"data:application/pdf;base64,{base64_pdf}"
        
        payload = {
            "model": GEMINI_MODELS[0],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.extraction_prompt
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": pdf_file.name,
                                "file_data": data_url
                            }
                        }
                    ]
                }
            ],
            "temperature": 0,
            "max_tokens": 8000,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        last_error = None
        for model in GEMINI_MODELS:
            try:
                payload["model"] = model
                _logger.info(f"Attempting multimodal extraction with model: {model}")
                
                response = requests.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()
                result = response.json()
                
                if "choices" not in result or not result["choices"]:
                    raise PDFExtractionError("No response from OpenRouter API")
                
                message = result["choices"][0]["message"]
                content = message.get("content", "")
                reasoning = message.get("reasoning", "")
                
                if not content and reasoning:
                    _logger.warning(f"Model {model} used reasoning mode, content may be incomplete")
                    content = reasoning
                
                if content:
                    _logger.info(f"Successfully extracted text using model: {model}")
                    return content
                else:
                    raise PDFExtractionError("Empty response from API")
                    
            except requests.RequestException as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    _logger.warning(f"Quota exceeded for {model}, trying next model...")
                    last_error = e
                    continue
                else:
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_detail = e.response.json()
                            error_msg = f"API error: {error_detail.get('error', str(e))}"
                        except:
                            error_msg = f"API error: {e.response.text[:200]}"
                    else:
                        error_msg = str(e)
                    _logger.error(f"Error with {model}: {error_msg}")
                    last_error = e
                    continue
            except Exception as e:
                _logger.error(f"Unexpected error with {model}: {str(e)}")
                last_error = e
                continue
        
        if last_error:
            error_msg = f"All Gemini models failed for PDF extraction. Last error: {str(last_error)}"
            raise PDFExtractionError(error_msg)
        
        raise PDFExtractionError("No Gemini models available for PDF extraction")

