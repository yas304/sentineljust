"""
Analysis Orchestrator
Coordinates all analysis components into a unified pipeline
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..models.schemas import (
    ClauseAnalysis,
    DocumentAnalysisResult,
    NegotiationSummary,
    ProcessingStatus
)
from .pdf_processor import PDFProcessor
from .clause_segmenter import ClauseSegmenter, Clause
from .gemini_engine import GeminiEngine, GeminiAPIError
from .fallback_engine import FallbackEngine
from .rag_pipeline import RAGPipeline
from .risk_scorer import RiskScorer
from .validator import ResponseValidator

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """
    Orchestrates the complete contract analysis pipeline.
    Coordinates PDF processing, clause segmentation, analysis, and risk scoring.
    """
    
    def __init__(self):
        # Initialize all components
        self.pdf_processor = PDFProcessor()
        self.clause_segmenter = ClauseSegmenter()
        self.gemini_engine = GeminiEngine()
        self.fallback_engine = FallbackEngine()
        self.rag_pipeline = RAGPipeline()
        self.risk_scorer = RiskScorer()
        self.validator = ResponseValidator()
        
        # Processing state
        self.processing_status: Dict[str, Dict[str, Any]] = {}
    
    async def process_document(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process a PDF document and extract text.
        
        Returns:
            Dictionary with document_id and processing metadata
        """
        result = self.pdf_processor.process(file_content, filename)
        
        document_id = result['document_id']
        
        # Initialize status
        self.processing_status[document_id] = {
            'status': ProcessingStatus.PENDING,
            'progress': 0.0,
            'message': 'Document uploaded',
            'filename': filename,
            'text': result['text'],
            'metadata': {
                'pdf_type': result.get('pdf_type'),
                'char_count': result.get('char_count'),
                'word_count': result.get('word_count'),
                'cached': result.get('cached', False)
            }
        }
        
        return {
            'document_id': document_id,
            'filename': filename,
            'status': ProcessingStatus.PENDING,
            'metadata': self.processing_status[document_id]['metadata']
        }
    
    async def analyze_document(
        self,
        document_id: str,
        include_negotiation: bool = True
    ) -> DocumentAnalysisResult:
        """
        Perform full analysis on a processed document.
        
        Args:
            document_id: ID of the processed document
            include_negotiation: Whether to include negotiation strategies
            
        Returns:
            Complete DocumentAnalysisResult
        """
        if document_id not in self.processing_status:
            raise ValueError(f"Document not found: {document_id}")
        
        status = self.processing_status[document_id]
        text = status.get('text', '')
        filename = status.get('filename', 'unknown.pdf')
        
        if not text:
            raise ValueError("No text available for analysis")
        
        # Update status
        status['status'] = ProcessingStatus.PROCESSING
        status['progress'] = 10.0
        status['message'] = 'Segmenting clauses...'
        
        try:
            # Step 1: Segment clauses
            clauses = self.clause_segmenter.segment(text)
            status['progress'] = 20.0
            status['message'] = f'Segmented {len(clauses)} clauses'
            
            # Step 2: Retrieve similar clauses from RAG
            status['progress'] = 30.0
            status['message'] = 'Retrieving similar clauses...'
            
            clause_dicts = [{'id': c.id, 'text': c.text} for c in clauses]
            rag_context = await self.rag_pipeline.retrieve_for_clauses(clause_dicts)
            
            status['progress'] = 40.0
            status['message'] = 'Analyzing clauses...'
            
            # Step 3: Analyze clauses
            analyzed_clauses = await self._analyze_clauses_with_fallback(
                clauses, 
                rag_context
            )
            
            status['progress'] = 80.0
            status['message'] = 'Calculating risk score...'
            
            # Step 4: Calculate risk score
            risk_result = self.risk_scorer.calculate_risk_score(analyzed_clauses)
            
            # Step 5: Generate negotiation summary
            negotiation_summary = self._build_negotiation_summary(analyzed_clauses)
            
            # Step 6: Generate improvements list
            improvements = self._generate_improvements(analyzed_clauses)
            
            # Step 7: Generate final summary
            final_summary = await self._generate_final_summary(
                analyzed_clauses, 
                risk_result
            )
            
            status['progress'] = 100.0
            status['status'] = ProcessingStatus.COMPLETED
            status['message'] = 'Analysis complete'
            
            # Build result
            result = DocumentAnalysisResult(
                document_id=document_id,
                filename=filename,
                processed_at=datetime.utcnow(),
                overall_risk_score=risk_result.risk_score,
                risk_summary=risk_result.summary,
                clauses=analyzed_clauses,
                negotiation_summary=negotiation_summary,
                improvements=improvements,
                final_summary=final_summary,
                metadata={
                    **status.get('metadata', {}),
                    'clause_count': len(analyzed_clauses),
                    'risk_breakdown': risk_result.breakdown,
                    'confidence': risk_result.confidence
                }
            )
            
            status['result'] = result
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            status['status'] = ProcessingStatus.FAILED
            status['message'] = str(e)
            raise
    
    async def _analyze_clauses_with_fallback(
        self,
        clauses: List[Clause],
        rag_context: Dict[str, List[Dict[str, Any]]]
    ) -> List[ClauseAnalysis]:
        """
        Analyze clauses using Gemini with fallback to local engine.
        """
        analyzed = []
        gemini_failures = 0
        
        for clause in clauses:
            rag_data = rag_context.get(clause.id, [])
            
            # Try Gemini first
            try:
                result = await self.gemini_engine.analyze_clause(
                    clause.text,
                    rag_data
                )
                
                if result:
                    # Validate result
                    validated = self.validator.cross_check_with_rag(result, rag_data)
                    validated.id = clause.id
                    analyzed.append(validated)
                    continue
                    
            except GeminiAPIError as e:
                logger.warning(f"Gemini failed for clause {clause.id}: {e}")
                gemini_failures += 1
            except Exception as e:
                logger.error(f"Unexpected error analyzing clause {clause.id}: {e}")
                gemini_failures += 1
            
            # Fallback to local engine
            fallback_result = self.fallback_engine.analyze_clause(
                clause.text,
                rag_data
            )
            fallback_result.id = clause.id
            analyzed.append(fallback_result)
        
        if gemini_failures > 0:
            logger.info(f"Used fallback engine for {gemini_failures}/{len(clauses)} clauses")
        
        return analyzed
    
    def _build_negotiation_summary(
        self,
        clauses: List[ClauseAnalysis]
    ) -> NegotiationSummary:
        """Build prioritized negotiation summary"""
        priority_items = self.risk_scorer.get_priority_items(clauses)
        
        return NegotiationSummary(
            high_priority=priority_items['high_priority'],
            medium_priority=priority_items['medium_priority'],
            low_priority=priority_items['low_priority']
        )
    
    def _generate_improvements(
        self,
        clauses: List[ClauseAnalysis]
    ) -> List[str]:
        """Generate list of recommended improvements"""
        improvements = []
        
        # High-risk clauses first
        high_risk = [c for c in clauses if c.risk_level == 'high']
        for clause in high_risk[:5]:  # Top 5
            improvements.append(
                f"[{clause.type.upper()}] {clause.suggestion}"
            )
        
        # Medium-risk with high leverage
        medium_high_leverage = [
            c for c in clauses 
            if c.risk_level == 'medium' and c.negotiation.leverage == 'high'
        ]
        for clause in medium_high_leverage[:3]:
            improvements.append(
                f"[{clause.type.upper()}] {clause.suggestion}"
            )
        
        # Add general recommendations
        if not improvements:
            improvements.append("Review contract terms with legal counsel before signing")
        
        return improvements[:10]  # Limit to 10 items
    
    async def _generate_final_summary(
        self,
        clauses: List[ClauseAnalysis],
        risk_result
    ) -> str:
        """Generate final summary text"""
        try:
            # Try Gemini for summary
            return await self.gemini_engine.generate_document_summary(clauses)
        except Exception:
            # Fallback to risk summary
            return risk_result.summary
    
    def get_status(self, document_id: str) -> Dict[str, Any]:
        """Get current processing status for a document"""
        if document_id not in self.processing_status:
            return {
                'status': 'not_found',
                'message': 'Document not found'
            }
        
        status = self.processing_status[document_id]
        return {
            'status': status.get('status', ProcessingStatus.PENDING),
            'progress': status.get('progress', 0.0),
            'message': status.get('message', ''),
            'result': status.get('result')
        }
    
    async def analyze_single_clause(
        self,
        clause_text: str
    ) -> ClauseAnalysis:
        """
        Analyze a single clause (for testing or API use).
        """
        # Get RAG context
        rag_data = await self.rag_pipeline.retrieve_similar(clause_text)
        
        # Try Gemini
        try:
            result = await self.gemini_engine.analyze_clause(clause_text, rag_data)
            if result:
                return self.validator.cross_check_with_rag(result, rag_data)
        except Exception as e:
            logger.warning(f"Gemini failed: {e}")
        
        # Fallback
        return self.fallback_engine.analyze_clause(clause_text, rag_data)
