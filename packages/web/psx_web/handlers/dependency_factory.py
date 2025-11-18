"""Dependency factory for web handlers to avoid circular imports."""

from typing import Optional


class DependencyFactory:
    """Factory for creating dependencies with lazy loading to avoid circular imports."""
    
    _price_repo = None
    _analysis_repo = None
    _technical_analyzer = None
    _financial_analyzer = None
    _recommendation_engine = None
    _sheets_client = None
    
    @staticmethod
    def get_price_repository():
        """Get price repository instance."""
        if DependencyFactory._price_repo is None:
            from psx_web.handlers.price_repository import WebPriceRepository
            DependencyFactory._price_repo = WebPriceRepository()
        return DependencyFactory._price_repo
    
    @staticmethod
    def get_analysis_repository():
        """Get analysis repository instance."""
        if DependencyFactory._analysis_repo is None:
            class SimpleAnalysisRepository:
                """Simple analysis repository that avoids circular imports."""
                
                def save(self, analysis):
                    pass
                
                def get_latest(self, symbol: str):
                    return None
                
                def get_previous_state(self, symbol: str, date):
                    return None
            
            DependencyFactory._analysis_repo = SimpleAnalysisRepository()
        return DependencyFactory._analysis_repo
    
    @staticmethod
    def get_technical_analyzer():
        """Get technical analyzer instance."""
        if DependencyFactory._technical_analyzer is None:
            from psx_analysis.technical_analysis.analyzers import TechnicalAnalyzer
            DependencyFactory._technical_analyzer = TechnicalAnalyzer()
        return DependencyFactory._technical_analyzer
    
    @staticmethod
    def get_financial_analyzer():
        """Get financial analyzer instance."""
        if DependencyFactory._financial_analyzer is None:
            from psx_analysis.financial_analysis.analyzers import FinancialAnalyzer
            DependencyFactory._financial_analyzer = FinancialAnalyzer()
        return DependencyFactory._financial_analyzer
    
    @staticmethod
    def get_recommendation_engine():
        """Get recommendation engine instance."""
        if DependencyFactory._recommendation_engine is None:
            from psx_analysis.domain.services.recommendation_engine import RecommendationEngine
            DependencyFactory._recommendation_engine = RecommendationEngine()
        return DependencyFactory._recommendation_engine
    
    @staticmethod
    def get_sheets_service():
        """Get sheets service instance (not available in web package)."""
        return None
    

