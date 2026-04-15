"""
Utility Helper Functions
"""

import re
import hashlib
import html
from typing import Optional


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text for safe processing.
    
    - Removes HTML tags
    - Escapes special characters
    - Removes control characters
    - Optionally truncates
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Escape HTML entities
    text = html.unescape(text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length - 3] + "..."
    
    return text.strip()


def generate_document_id(content: bytes) -> str:
    """Generate a unique document ID from content hash"""
    return hashlib.sha256(content).hexdigest()


def format_risk_score(score: float) -> dict:
    """
    Format risk score with color and label.
    
    Returns:
        Dictionary with score, label, and color
    """
    if score >= 70:
        return {
            "score": round(score, 1),
            "label": "High Risk",
            "color": "#F44336",
            "bg_color": "#FFEBEE"
        }
    elif score >= 40:
        return {
            "score": round(score, 1),
            "label": "Medium Risk",
            "color": "#FF9800",
            "bg_color": "#FFF3E0"
        }
    else:
        return {
            "score": round(score, 1),
            "label": "Low Risk",
            "color": "#4CAF50",
            "bg_color": "#E8F5E9"
        }


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_numbers(text: str) -> list:
    """Extract all numbers from text"""
    return re.findall(r'\d+(?:\.\d+)?', text)


def normalize_clause_type(clause_type: str) -> str:
    """Normalize clause type string"""
    return clause_type.lower().strip().replace(' ', '_').replace('-', '_')
