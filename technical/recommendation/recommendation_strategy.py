from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class RecommendationStrategy(ABC):
    @abstractmethod
    def evaluate(self, indicators: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[str, float, str]:
        pass

