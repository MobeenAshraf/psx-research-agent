"""Model configuration for financial analysis workflow."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ModelConfig:
    """Configuration for model selection per analysis step."""
    
    # Default extraction model - fast, cheap, good for structured JSON extraction
    DEFAULT_EXTRACTION_MODEL: str = os.getenv(
        'EXTRACTION_MODEL',
        'google/gemini-3-flash-preview'
    )
    
    # Default analysis model - better reasoning for qualitative assessment
    DEFAULT_ANALYSIS_MODEL: str = os.getenv(
        'ANALYSIS_MODEL',
        'deepseek/deepseek-v4.1-flash-1017'
    )
    
    # Default decision model - strong reasoning for decision-making
    DEFAULT_DECISION_MODEL: str = os.getenv(
        'DECISION_MODEL',
        'deepseek/deepseek-v4.1-flash-1017'
    )
    
    # Models that support multimodal PDF processing
    GEMINI_MODELS = [
        "google/gemini-3-pro-preview",
        "google/gemini-3-flash-preview"
    ]
    
    @classmethod
    def is_multimodal_model(cls, model: str) -> bool:
        """Check if model supports multimodal PDF processing."""
        return model in cls.GEMINI_MODELS
    
    @classmethod
    def get_extraction_model(cls, user_model: Optional[str] = None) -> str:
        """Get model for data extraction step."""
        if user_model and user_model != "auto":
            return user_model
        return cls.DEFAULT_EXTRACTION_MODEL
    
    @classmethod
    def get_analysis_model(cls, user_model: Optional[str] = None) -> str:
        """Get model for analysis step."""
        if user_model and user_model != "auto":
            return user_model
        return cls.DEFAULT_ANALYSIS_MODEL
    
    @classmethod
    def get_decision_model(cls, user_model: Optional[str] = None) -> str:
        """Get model for decision step."""
        if user_model and user_model != "auto":
            return user_model
        return cls.DEFAULT_DECISION_MODEL
    
    @classmethod
    def normalize_model_name(cls, model: Optional[str], is_extraction: bool = True) -> str:
        """Normalize 'auto' to actual default model name for consistent caching."""
        return cls.get_extraction_model(model) if is_extraction else cls.get_analysis_model(model)

