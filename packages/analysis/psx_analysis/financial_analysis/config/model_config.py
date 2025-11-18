"""Model configuration for financial analysis workflow."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ModelConfig:
    """Configuration for model selection per analysis step."""
    
    # Extraction model - fast, cheap, good for structured JSON extraction
    EXTRACTION_MODEL: str = os.getenv(
        'EXTRACTION_MODEL',
        'openai/gpt-4o-mini'
    )
    
    # Analysis model - better reasoning for qualitative assessment
    ANALYSIS_MODEL: str = os.getenv(
        'ANALYSIS_MODEL',
        'openai/gpt-4o'
    )
    
    @classmethod
    def get_extraction_model(cls) -> str:
        """Get model for data extraction step."""
        return cls.EXTRACTION_MODEL
    
    @classmethod
    def get_analysis_model(cls) -> str:
        """Get model for analysis step."""
        return cls.ANALYSIS_MODEL

