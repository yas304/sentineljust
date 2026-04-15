"""
API Routes
FastAPI endpoints for Sentinel Core
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ..models.schemas import (
    UploadResponse,
    AnalysisStatusResponse,
    DocumentAnalysisResult,
    ClauseAnalysis,
    ProcessingStatus,
    ErrorResponse
)
from ..core import AnalysisOrchestrator, RAGPipeline
from .dependencies import get_orchestrator, get_rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Contract Analysis"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        500: {"model": ErrorResponse, "description": "Processing error"}
    }
)
async def upload_document(
    file: UploadFile = File(...),
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator)
):
    """
    Upload a PDF contract for analysis.
    
    - **file**: PDF file to analyze (max 50MB)
    
    Returns document ID for tracking analysis progress.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        content = await file.read()
        
        result = await orchestrator.process_document(content, file.filename)
        
        return UploadResponse(
            document_id=result['document_id'],
            filename=result['filename'],
            status=ProcessingStatus.PENDING,
            message="Document uploaded successfully. Ready for analysis."
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@router.post(
    "/analyze/{document_id}",
    response_model=DocumentAnalysisResult,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Analysis error"}
    }
)
async def analyze_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    include_negotiation: bool = True,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator)
):
    """
    Analyze a previously uploaded document.
    
    - **document_id**: ID returned from upload endpoint
    - **include_negotiation**: Include negotiation strategies (default: true)
    
    Returns complete analysis with risk score, clause analysis, and recommendations.
    """
    try:
        result = await orchestrator.analyze_document(
            document_id,
            include_negotiation=include_negotiation
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get(
    "/status/{document_id}",
    response_model=AnalysisStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"}
    }
)
async def get_analysis_status(
    document_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator)
):
    """
    Check the analysis status of a document.
    
    - **document_id**: ID returned from upload endpoint
    
    Returns current processing status and progress.
    """
    status = orchestrator.get_status(document_id)
    
    if status.get('status') == 'not_found':
        raise HTTPException(status_code=404, detail="Document not found")
    
    return AnalysisStatusResponse(
        document_id=document_id,
        status=status['status'],
        progress=status.get('progress', 0.0),
        message=status.get('message', ''),
        result=status.get('result')
    )


@router.post(
    "/analyze-clause",
    response_model=ClauseAnalysis,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Analysis error"}
    }
)
async def analyze_single_clause(
    clause_text: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator)
):
    """
    Analyze a single clause (for testing or quick analysis).
    
    - **clause_text**: The clause text to analyze
    
    Returns clause analysis with risk assessment and negotiation strategy.
    """
    if not clause_text or len(clause_text.strip()) < 20:
        raise HTTPException(
            status_code=400, 
            detail="Clause text must be at least 20 characters"
        )
    
    try:
        result = await orchestrator.analyze_single_clause(clause_text)
        return result
    except Exception as e:
        logger.error(f"Clause analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post(
    "/rag/load-dataset",
    responses={
        500: {"model": ErrorResponse, "description": "Load error"}
    }
)
async def load_rag_dataset(
    dataset_path: str = "data/clause_dataset.json",
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Load clause dataset into RAG pipeline.
    
    - **dataset_path**: Path to JSON dataset file
    
    Returns number of clauses loaded.
    """
    try:
        count = await rag_pipeline.load_dataset(dataset_path)
        return {"message": f"Loaded {count} clauses into RAG database"}
    except Exception as e:
        logger.error(f"Dataset load failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {str(e)}")


@router.get("/rag/stats")
async def get_rag_stats(
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Get statistics about the RAG database.
    
    Returns clause counts by type and risk level.
    """
    stats = await rag_pipeline.get_stats()
    return stats


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Sentinel Core"}
