"""
Sentinel Core Data Models
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LeverageLevel(str, Enum):
    """Negotiation leverage level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Request Models
class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    filename: str
    content_type: str = "application/pdf"


class AnalysisRequest(BaseModel):
    """Request model for document analysis"""
    document_id: str
    include_negotiation: bool = True
    risk_threshold: Optional[float] = None


# Core Analysis Models
class NegotiationStrategy(BaseModel):
    """Negotiation strategy for a clause"""
    objective: str = Field(..., description="Primary negotiation objective")
    reason: str = Field(..., description="Rationale for negotiation")
    suggested_change: str = Field(..., description="Specific suggested modification")
    leverage: LeverageLevel = Field(..., description="Negotiation leverage level")
    
    class Config:
        use_enum_values = True


class ClauseAnalysis(BaseModel):
    """Analysis result for a single clause"""
    id: Optional[str] = None
    text: str = Field(..., description="Original clause text")
    type: str = Field(..., description="Clause type classification")
    risk_level: RiskLevel = Field(..., description="Risk level assessment")
    issue: str = Field(..., description="Identified issue or concern")
    suggestion: str = Field(..., description="Recommended improvement")
    negotiation: NegotiationStrategy = Field(..., description="Negotiation strategy")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="gemini", description="Analysis source (gemini/fallback)")
    
    class Config:
        use_enum_values = True


class NegotiationSummary(BaseModel):
    """Prioritized negotiation summary"""
    high_priority: List[Dict[str, Any]] = Field(default_factory=list)
    medium_priority: List[Dict[str, Any]] = Field(default_factory=list)
    low_priority: List[Dict[str, Any]] = Field(default_factory=list)


class RiskScoreResult(BaseModel):
    """Risk scoring result"""
    risk_score: float = Field(..., ge=0, le=100)
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    breakdown: Optional[Dict[str, Any]] = None


class DocumentAnalysisResult(BaseModel):
    """Complete document analysis result"""
    document_id: str
    filename: str
    processed_at: datetime
    overall_risk_score: float = Field(..., ge=0, le=100)
    risk_summary: str
    clauses: List[ClauseAnalysis]
    negotiation_summary: NegotiationSummary
    improvements: List[str]
    final_summary: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# RAG Models
class ClauseEmbedding(BaseModel):
    """Clause with embedding for vector storage"""
    id: str
    clause_text: str
    clause_type: str
    risk_level: RiskLevel
    issue: str
    recommendation: str
    negotiation_hint: str
    embedding: Optional[List[float]] = None
    
    class Config:
        use_enum_values = True


class RetrievedClause(BaseModel):
    """Retrieved clause from RAG pipeline"""
    clause_text: str
    clause_type: str
    risk_level: str
    issue: str
    recommendation: str
    negotiation_hint: str
    similarity_score: float


# Response Models
class UploadResponse(BaseModel):
    """Response for document upload"""
    document_id: str
    filename: str
    status: ProcessingStatus
    message: str
    
    class Config:
        use_enum_values = True


class AnalysisStatusResponse(BaseModel):
    """Response for analysis status check"""
    document_id: str
    status: ProcessingStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str
    result: Optional[DocumentAnalysisResult] = None
    
    class Config:
        use_enum_values = True


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Validation helpers
class GeminiResponse(BaseModel):
    """Expected Gemini API response structure"""
    type: str
    risk_level: str
    issue: str
    suggestion: str
    negotiation: Dict[str, str]
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        if v.lower() not in ['low', 'medium', 'high']:
            raise ValueError(f'Invalid risk level: {v}')
        return v.lower()
    
    @validator('negotiation')
    def validate_negotiation(cls, v):
        required_keys = ['objective', 'reason', 'suggested_change', 'leverage']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Missing negotiation key: {key}')
        if v.get('leverage', '').lower() not in ['low', 'medium', 'high']:
            raise ValueError(f'Invalid leverage level: {v.get("leverage")}')
        return v
