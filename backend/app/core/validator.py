"""
Response Validator
Validates and normalizes outputs from Gemini and fallback engines
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import ValidationError

from ..config import CLAUSE_TYPES, RISK_INDICATORS
from ..models.schemas import (
    ClauseAnalysis, 
    NegotiationStrategy,
    GeminiResponse,
    RiskLevel,
    LeverageLevel
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    pass


class ResponseValidator:
    """
    Validates and normalizes responses from analysis engines.
    Ensures consistency and cross-checks with RAG data.
    """
    
    def __init__(self):
        self.valid_clause_types = set(CLAUSE_TYPES)
        self.valid_risk_levels = {'low', 'medium', 'high'}
        self.valid_leverage_levels = {'low', 'medium', 'high'}
    
    def validate_json_structure(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Validate that response is valid JSON with expected structure.
        
        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """
        # Clean response
        response_text = response_text.strip()
        
        # Remove markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON: {str(e)}"
        
        # Validate structure
        required_fields = ['type', 'risk_level', 'issue', 'suggestion', 'negotiation']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return False, None, f"Missing required fields: {', '.join(missing)}"
        
        # Validate negotiation structure
        if isinstance(data.get('negotiation'), dict):
            neg_required = ['objective', 'reason', 'suggested_change', 'leverage']
            neg_missing = [f for f in neg_required if f not in data['negotiation']]
            if neg_missing:
                return False, None, f"Missing negotiation fields: {', '.join(neg_missing)}"
        else:
            return False, None, "Negotiation must be an object"
        
        return True, data, ""
    
    def validate_risk_level(self, risk_level: str) -> str:
        """Validate and normalize risk level"""
        normalized = risk_level.lower().strip()
        
        if normalized in self.valid_risk_levels:
            return normalized
        
        # Try to infer from common variations
        if 'high' in normalized or 'severe' in normalized or 'critical' in normalized:
            return 'high'
        elif 'low' in normalized or 'minor' in normalized or 'minimal' in normalized:
            return 'low'
        else:
            return 'medium'  # Default to medium if uncertain
    
    def validate_leverage_level(self, leverage: str) -> str:
        """Validate and normalize leverage level"""
        normalized = leverage.lower().strip()
        
        if normalized in self.valid_leverage_levels:
            return normalized
        
        if 'high' in normalized or 'strong' in normalized:
            return 'high'
        elif 'low' in normalized or 'weak' in normalized:
            return 'low'
        else:
            return 'medium'
    
    def validate_clause_type(self, clause_type: str) -> str:
        """Validate and normalize clause type"""
        normalized = clause_type.lower().strip().replace(' ', '_')
        
        if normalized in self.valid_clause_types:
            return normalized
        
        # Try to map common variations
        type_mappings = {
            'terminate': 'termination',
            'end': 'termination',
            'cancel': 'termination',
            'indemnity': 'indemnification',
            'hold_harmless': 'indemnification',
            'ip': 'intellectual_property',
            'nda': 'confidentiality',
            'non_disclosure': 'confidentiality',
            'limit_of_liability': 'liability',
            'damages': 'liability',
            'arbitrate': 'dispute_resolution',
            'mediate': 'dispute_resolution',
            'jurisdiction': 'governing_law',
            'choice_of_law': 'governing_law',
        }
        
        for key, value in type_mappings.items():
            if key in normalized:
                return value
        
        return 'unknown'
    
    def validate_text_field(self, field: str, field_name: str, max_length: int = 2000) -> str:
        """Validate text field is non-empty and within limits"""
        if not field or not isinstance(field, str):
            return f"[{field_name} not provided]"
        
        text = field.strip()
        
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
        
        return text
    
    def cross_check_with_rag(
        self,
        analysis: ClauseAnalysis,
        rag_data: List[Dict[str, Any]]
    ) -> ClauseAnalysis:
        """
        Cross-check analysis with RAG retrieved data.
        Adjusts risk levels if there's significant disagreement.
        """
        if not rag_data:
            return analysis
        
        # Get risk levels from RAG data
        rag_risks = [r.get('risk_level', 'medium').lower() for r in rag_data]
        
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        reverse_order = {0: 'low', 1: 'medium', 2: 'high'}
        
        # Calculate average RAG risk
        avg_rag_risk = sum(risk_order.get(r, 1) for r in rag_risks) / len(rag_risks)
        
        # Get current analysis risk
        current_risk = risk_order.get(analysis.risk_level, 1)
        
        # If significant disagreement (more than 0.5 level difference), adjust
        if abs(avg_rag_risk - current_risk) > 0.5:
            # Use the more conservative (higher) risk
            adjusted_risk = max(current_risk, round(avg_rag_risk))
            adjusted_level = reverse_order.get(adjusted_risk, 'medium')
            
            if adjusted_level != analysis.risk_level:
                logger.info(
                    f"Adjusted risk from {analysis.risk_level} to {adjusted_level} "
                    f"based on RAG cross-check"
                )
                analysis.risk_level = adjusted_level
        
        return analysis
    
    def normalize_output(
        self,
        data: Dict[str, Any],
        clause_text: str
    ) -> ClauseAnalysis:
        """
        Normalize and validate a raw response into ClauseAnalysis.
        
        Args:
            data: Raw response data
            clause_text: Original clause text
            
        Returns:
            Validated ClauseAnalysis object
        """
        # Validate and normalize fields
        clause_type = self.validate_clause_type(data.get('type', 'unknown'))
        risk_level = self.validate_risk_level(data.get('risk_level', 'medium'))
        issue = self.validate_text_field(data.get('issue', ''), 'issue')
        suggestion = self.validate_text_field(data.get('suggestion', ''), 'suggestion')
        
        # Validate negotiation
        neg_data = data.get('negotiation', {})
        if not isinstance(neg_data, dict):
            neg_data = {}
        
        negotiation = NegotiationStrategy(
            objective=self.validate_text_field(
                neg_data.get('objective', 'Review clause terms'), 
                'objective',
                500
            ),
            reason=self.validate_text_field(
                neg_data.get('reason', 'Standard contract review'), 
                'reason',
                500
            ),
            suggested_change=self.validate_text_field(
                neg_data.get('suggested_change', 'Negotiate terms as needed'), 
                'suggested_change',
                1000
            ),
            leverage=self.validate_leverage_level(neg_data.get('leverage', 'medium'))
        )
        
        return ClauseAnalysis(
            text=clause_text,
            type=clause_type,
            risk_level=risk_level,
            issue=issue,
            suggestion=suggestion,
            negotiation=negotiation,
            confidence=0.8,  # Default confidence for validated responses
            source="gemini"
        )
    
    def validate_full_response(
        self,
        response_text: str,
        clause_text: str,
        rag_data: List[Dict[str, Any]] = None
    ) -> Optional[ClauseAnalysis]:
        """
        Full validation pipeline for Gemini responses.
        
        Args:
            response_text: Raw response from Gemini
            clause_text: Original clause text
            rag_data: Retrieved similar clauses for cross-check
            
        Returns:
            Validated ClauseAnalysis or None if validation fails
        """
        # Validate JSON structure
        is_valid, data, error = self.validate_json_structure(response_text)
        
        if not is_valid:
            logger.warning(f"JSON validation failed: {error}")
            return None
        
        # Normalize output
        try:
            analysis = self.normalize_output(data, clause_text)
        except Exception as e:
            logger.warning(f"Output normalization failed: {e}")
            return None
        
        # Cross-check with RAG data
        if rag_data:
            analysis = self.cross_check_with_rag(analysis, rag_data)
        
        return analysis
    
    def validate_batch_response(
        self,
        analyses: List[Optional[ClauseAnalysis]]
    ) -> Tuple[List[ClauseAnalysis], int, int]:
        """
        Validate a batch of clause analyses.
        
        Returns:
            Tuple of (valid_analyses, valid_count, failed_count)
        """
        valid = []
        failed = 0
        
        for analysis in analyses:
            if analysis is None:
                failed += 1
            elif self._is_valid_analysis(analysis):
                valid.append(analysis)
            else:
                failed += 1
        
        return valid, len(valid), failed
    
    def _is_valid_analysis(self, analysis: ClauseAnalysis) -> bool:
        """Check if analysis object is valid"""
        # Must have non-empty essential fields
        if not analysis.text or len(analysis.text.strip()) < 10:
            return False
        
        if not analysis.type or analysis.type == 'unknown':
            # Unknown is acceptable but log it
            logger.debug("Analysis has unknown clause type")
        
        if not analysis.issue or len(analysis.issue.strip()) < 5:
            return False
        
        if not analysis.suggestion or len(analysis.suggestion.strip()) < 5:
            return False
        
        return True
