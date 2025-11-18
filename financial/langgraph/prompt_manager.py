"""Prompt loading and caching for LangGraph workflow."""

from pathlib import Path
from typing import Optional


BASE_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class PromptManager:
    """Manages prompt loading and caching."""
    
    SYSTEM_PROMPT_FILE = BASE_PROMPT_DIR / "1_system_prompt_expert_analyst.md"
    EXTRACTION_PROMPT_FILE = BASE_PROMPT_DIR / "investor_extraction_prompt.md"
    ANALYSIS_PROMPT_FILE = BASE_PROMPT_DIR / "investor_analysis_prompt.md"
    
    def __init__(self):
        self._system_prompt_cache: Optional[str] = None
        self._extraction_prompt_cache: Optional[str] = None
        self._analysis_prompt_cache: Optional[str] = None
    
    def load_system_prompt(self) -> str:
        """Load system prompt from file."""
        if self._system_prompt_cache:
            return self._system_prompt_cache
        
        if not self.SYSTEM_PROMPT_FILE.exists():
            self._system_prompt_cache = "You are a financial data extraction and analysis specialist. Extract accurate numerical data and provide insightful analysis."
            return self._system_prompt_cache
        
        self._system_prompt_cache = self.SYSTEM_PROMPT_FILE.read_text(encoding='utf-8')
        return self._system_prompt_cache
    
    def load_extraction_prompt(self) -> str:
        """Load extraction prompt from file."""
        if self._extraction_prompt_cache:
            return self._extraction_prompt_cache
        
        if not self.EXTRACTION_PROMPT_FILE.exists():
            raise FileNotFoundError(f"Extraction prompt file not found: {self.EXTRACTION_PROMPT_FILE}")
        
        self._extraction_prompt_cache = self.EXTRACTION_PROMPT_FILE.read_text(encoding='utf-8')
        return self._extraction_prompt_cache
    
    def load_analysis_prompt(self) -> str:
        """Load analysis prompt from file."""
        if self._analysis_prompt_cache:
            return self._analysis_prompt_cache
        
        if not self.ANALYSIS_PROMPT_FILE.exists():
            raise FileNotFoundError(f"Analysis prompt file not found: {self.ANALYSIS_PROMPT_FILE}")
        
        self._analysis_prompt_cache = self.ANALYSIS_PROMPT_FILE.read_text(encoding='utf-8')
        return self._analysis_prompt_cache

