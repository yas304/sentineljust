"""
API Dependencies
Dependency injection for FastAPI endpoints
"""

from functools import lru_cache
from ..core import AnalysisOrchestrator, RAGPipeline


@lru_cache()
def get_orchestrator() -> AnalysisOrchestrator:
    """Get singleton AnalysisOrchestrator instance"""
    return AnalysisOrchestrator()


@lru_cache()
def get_rag_pipeline() -> RAGPipeline:
    """Get singleton RAGPipeline instance"""
    return RAGPipeline()
