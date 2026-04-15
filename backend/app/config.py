"""
Sentinel Core Configuration
Manages all environment variables and system settings
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Sentinel Core"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Keys
    GEMINI_API_KEY: str
    
    # Supabase Configuration (optional - used by frontend)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list = ["application/pdf"]
    UPLOAD_DIR: str = "./uploads"
    CACHE_DIR: str = "./cache"
    
    # Processing Settings
    GEMINI_TIMEOUT: int = 5
    GEMINI_RETRY_COUNT: int = 2
    BATCH_SIZE: int = 10
    
    # RAG Settings
    EMBEDDING_MODEL: str = "models/embedding-001"
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Risk Scoring Weights
    HIGH_RISK_WEIGHT: int = 20
    MISSING_CLAUSE_WEIGHT: int = 15
    AMBIGUITY_WEIGHT: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Risk level definitions
RISK_LEVELS = {
    "low": {"score": 0, "color": "#4CAF50"},
    "medium": {"score": 10, "color": "#FF9800"},
    "high": {"score": 20, "color": "#F44336"}
}

# Clause types recognized by the system
CLAUSE_TYPES = [
    "termination",
    "indemnification",
    "liability",
    "confidentiality",
    "intellectual_property",
    "payment",
    "warranty",
    "force_majeure",
    "dispute_resolution",
    "governing_law",
    "assignment",
    "notice",
    "amendment",
    "severability",
    "entire_agreement",
    "non_compete",
    "non_solicitation",
    "data_protection",
    "compliance",
    "insurance",
    "audit_rights",
    "representations",
    "covenants",
    "conditions_precedent",
    "default",
    "remedies",
    "unknown"
]

# Keywords for rule-based classification
CLAUSE_KEYWORDS = {
    "termination": ["terminate", "termination", "end", "cancel", "cancellation", "expire", "expiration", "notice period"],
    "indemnification": ["indemnify", "indemnification", "hold harmless", "defend", "indemnitor", "indemnitee"],
    "liability": ["liability", "liable", "limitation of liability", "cap", "damages", "consequential"],
    "confidentiality": ["confidential", "confidentiality", "non-disclosure", "nda", "proprietary", "trade secret"],
    "intellectual_property": ["intellectual property", "ip", "patent", "copyright", "trademark", "license", "ownership"],
    "payment": ["payment", "pay", "invoice", "fee", "compensation", "price", "cost", "billing"],
    "warranty": ["warranty", "warranties", "warrant", "guarantee", "representation"],
    "force_majeure": ["force majeure", "act of god", "unforeseen", "beyond control", "pandemic", "natural disaster"],
    "dispute_resolution": ["dispute", "arbitration", "mediation", "litigation", "resolution", "settle"],
    "governing_law": ["governing law", "jurisdiction", "applicable law", "venue", "forum"],
    "assignment": ["assign", "assignment", "transfer", "delegate", "assignee"],
    "notice": ["notice", "notification", "written notice", "notify", "inform"],
    "amendment": ["amend", "amendment", "modify", "modification", "change"],
    "severability": ["severability", "severable", "invalid", "unenforceable"],
    "entire_agreement": ["entire agreement", "whole agreement", "complete agreement", "supersede"],
    "non_compete": ["non-compete", "noncompete", "compete", "competition", "competitive"],
    "non_solicitation": ["non-solicitation", "nonsolicitation", "solicit", "solicitation"],
    "data_protection": ["data protection", "gdpr", "privacy", "personal data", "data processing"],
    "compliance": ["compliance", "comply", "regulation", "regulatory", "law"],
    "insurance": ["insurance", "insure", "coverage", "policy", "underwriter"],
    "audit_rights": ["audit", "inspection", "review", "examine", "access to records"],
    "representations": ["represent", "representation", "declare", "declaration"],
    "covenants": ["covenant", "undertake", "undertaking", "agree to"],
    "conditions_precedent": ["condition precedent", "prior to", "before", "prerequisite"],
    "default": ["default", "breach", "fail", "failure", "violation"],
    "remedies": ["remedy", "remedies", "cure", "relief", "recourse"]
}

# Risk indicators for heuristic analysis
RISK_INDICATORS = {
    "high": [
        "unlimited liability",
        "sole discretion",
        "without cause",
        "immediately terminate",
        "no notice",
        "waive all rights",
        "perpetual",
        "irrevocable",
        "exclusive remedy",
        "no refund",
        "as-is",
        "no warranty"
    ],
    "medium": [
        "may terminate",
        "reasonable efforts",
        "material breach",
        "thirty (30) days",
        "mutual agreement",
        "subject to",
        "unless otherwise",
        "generally accepted"
    ],
    "low": [
        "sixty (60) days",
        "ninety (90) days",
        "written consent",
        "prior approval",
        "mutual consent",
        "jointly agree",
        "fair and reasonable"
    ]
}

# Ensure directories exist
Path(get_settings().UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(get_settings().CACHE_DIR).mkdir(parents=True, exist_ok=True)
