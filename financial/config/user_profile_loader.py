"""User profile loader and validator."""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class UserProfileLoader:
    """Load and validate user profile from JSON file."""
    
    DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[2] / "data" / "user_profile.json"
    
    @classmethod
    def load_profile(cls, profile_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load user profile from JSON file.
        
        Args:
            profile_path: Optional path to profile file. If None, uses default path.
            
        Returns:
            Dictionary containing user profile data.
            
        Raises:
            FileNotFoundError: If profile file doesn't exist.
            ValueError: If profile file is invalid JSON or missing required fields.
        """
        path = profile_path or cls.DEFAULT_PROFILE_PATH
        
        if not path.exists():
            raise FileNotFoundError(
                f"User profile file not found: {path}\n"
                f"Please create the profile file at: {path}"
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in user profile file {path}: {str(e)}"
            ) from e
        
        cls._validate_profile(profile)
        
        return profile
    
    @classmethod
    def _validate_profile(cls, profile: Dict[str, Any]) -> None:
        """
        Validate profile structure.
        
        Args:
            profile: Profile dictionary to validate.
            
        Raises:
            ValueError: If profile is missing required fields or has invalid structure.
        """
        required_fields = [
            "age",
            "objectives",
            "constraints",
            "current_portfolio",
            "income_and_spending",
            "risk_profile"
        ]
        
        missing_fields = [field for field in required_fields if field not in profile]
        if missing_fields:
            raise ValueError(
                f"User profile missing required fields: {', '.join(missing_fields)}"
            )
        
        if not isinstance(profile.get("age"), int):
            raise ValueError("User profile 'age' must be an integer")
        
        required_objectives = ["primary_goal", "time_horizon_years"]
        objectives = profile.get("objectives", {})
        missing_objectives = [
            field for field in required_objectives
            if field not in objectives
        ]
        if missing_objectives:
            raise ValueError(
                f"User profile 'objectives' missing required fields: {', '.join(missing_objectives)}"
            )
        
        required_constraints = ["halal_only"]
        constraints = profile.get("constraints", {})
        missing_constraints = [
            field for field in required_constraints
            if field not in constraints
        ]
        if missing_constraints:
            raise ValueError(
                f"User profile 'constraints' missing required fields: {', '.join(missing_constraints)}"
            )
        
        portfolio = profile.get("current_portfolio", {})
        if "symbols" not in portfolio:
            raise ValueError("User profile 'current_portfolio' must include 'symbols' field")
        
        if not isinstance(portfolio.get("symbols"), list):
            raise ValueError("User profile 'current_portfolio.symbols' must be a list")

