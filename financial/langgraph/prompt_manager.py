"""Prompt loading and caching for LangGraph workflow."""

from pathlib import Path
from typing import Optional, Dict, Any


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
    
    def load_system_prompt(self, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """Load system prompt from file, optionally including user profile context."""
        base_prompt = self._get_system_prompt_base()
        
        if user_profile:
            profile_context = self._format_user_profile_context(user_profile)
            return f"{base_prompt}\n\n{profile_context}"
        
        return base_prompt
    
    def _get_system_prompt_base(self) -> str:
        """Get base system prompt from cache or file."""
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
    
    def load_analysis_prompt(self, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """Load analysis prompt from file, optionally including user profile context."""
        base_prompt = self._get_analysis_prompt_base()
        
        if user_profile:
            profile_context = self._format_user_profile_context(user_profile)
            return f"{base_prompt}\n\n{profile_context}"
        
        return base_prompt
    
    def _get_analysis_prompt_base(self) -> str:
        """Get base analysis prompt from cache or file."""
        if self._analysis_prompt_cache:
            return self._analysis_prompt_cache
        
        if not self.ANALYSIS_PROMPT_FILE.exists():
            raise FileNotFoundError(f"Analysis prompt file not found: {self.ANALYSIS_PROMPT_FILE}")
        
        self._analysis_prompt_cache = self.ANALYSIS_PROMPT_FILE.read_text(encoding='utf-8')
        return self._analysis_prompt_cache
    
    def _format_user_profile_context(self, user_profile: Dict[str, Any]) -> str:
        """Format user profile data into prompt context."""
        context_parts = ["## User Profile Context"]
        
        if user_profile.get("age"):
            context_parts.append(f"- Age: {user_profile['age']}")
        
        if user_profile.get("risk_tolerance"):
            context_parts.append(f"- Risk Tolerance: {user_profile['risk_tolerance']}")
        
        if user_profile.get("investment_style"):
            context_parts.append(f"- Investment Style: {user_profile['investment_style']}")
        
        if user_profile.get("investment_horizon"):
            context_parts.append(f"- Investment Horizon: {user_profile['investment_horizon']}")
        
        if user_profile.get("investment_goals"):
            context_parts.append(f"- Investment Goals: {user_profile['investment_goals']}")
        
        if len(context_parts) == 1:
            return ""
        
        context_parts.append("\n**Note:** Tailor your analysis to align with the user's profile above.")
        
        return "\n".join(context_parts)

