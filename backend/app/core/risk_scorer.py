"""
Risk Scoring Engine
Deterministic risk calculation with Gemini assistance
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from ..config import get_settings, CLAUSE_TYPES
from ..models.schemas import ClauseAnalysis, RiskScoreResult

logger = logging.getLogger(__name__)


@dataclass
class RiskBreakdown:
    """Detailed risk breakdown"""
    high_risk_clauses: int
    medium_risk_clauses: int
    low_risk_clauses: int
    missing_clauses: List[str]
    ambiguous_clauses: int
    raw_score: float
    normalized_score: float
    

class RiskScorer:
    """
    Deterministic risk scoring engine.
    Final scores are computed locally for consistency and auditability.
    """
    
    # Essential clause types that should be present in most contracts
    ESSENTIAL_CLAUSES = [
        "termination",
        "liability",
        "indemnification",
        "confidentiality",
        "governing_law",
        "dispute_resolution"
    ]
    
    # High-priority clauses that significantly impact risk
    HIGH_PRIORITY_CLAUSES = [
        "termination",
        "liability",
        "indemnification",
        "intellectual_property",
        "non_compete"
    ]
    
    def __init__(self):
        self.settings = get_settings()
        
        # Scoring weights
        self.high_risk_weight = self.settings.HIGH_RISK_WEIGHT  # +20 per clause
        self.missing_clause_weight = self.settings.MISSING_CLAUSE_WEIGHT  # +15 per clause
        self.ambiguity_weight = self.settings.AMBIGUITY_WEIGHT  # +10 per clause
        
        # Risk level multipliers
        self.risk_multipliers = {
            'high': 1.0,
            'medium': 0.5,
            'low': 0.1
        }
        
        # Clause type importance weights
        self.clause_importance = {
            'termination': 1.5,
            'liability': 2.0,
            'indemnification': 1.8,
            'intellectual_property': 1.5,
            'confidentiality': 1.2,
            'non_compete': 1.3,
            'payment': 1.0,
            'warranty': 1.2,
            'force_majeure': 0.8,
            'dispute_resolution': 1.0,
            'governing_law': 0.8,
            'default': 1.0
        }
    
    def _identify_missing_clauses(
        self,
        analyzed_clauses: List[ClauseAnalysis]
    ) -> List[str]:
        """Identify essential clauses that are missing"""
        found_types = set(c.type.lower() for c in analyzed_clauses)
        missing = []
        
        for essential in self.ESSENTIAL_CLAUSES:
            if essential not in found_types:
                missing.append(essential)
        
        return missing
    
    def _count_ambiguous_clauses(
        self,
        analyzed_clauses: List[ClauseAnalysis]
    ) -> int:
        """Count clauses with ambiguous language"""
        ambiguous_count = 0
        
        ambiguous_indicators = [
            'vague',
            'unclear',
            'ambiguous',
            'not specific',
            'missing definition',
            'undefined'
        ]
        
        for clause in analyzed_clauses:
            issue_lower = clause.issue.lower()
            if any(ind in issue_lower for ind in ambiguous_indicators):
                ambiguous_count += 1
            elif clause.confidence < 0.5:
                ambiguous_count += 1
        
        return ambiguous_count
    
    def _calculate_clause_risk_contribution(
        self,
        clause: ClauseAnalysis
    ) -> float:
        """Calculate individual clause's contribution to overall risk"""
        # Base score from risk level
        risk_multiplier = self.risk_multipliers.get(clause.risk_level, 0.5)
        
        # Importance weight
        importance = self.clause_importance.get(
            clause.type.lower(), 
            self.clause_importance['default']
        )
        
        # Calculate contribution
        base_contribution = self.high_risk_weight * risk_multiplier * importance
        
        # Adjust by confidence (lower confidence = higher uncertainty = slightly higher risk)
        confidence_adjustment = 1 + (1 - clause.confidence) * 0.2
        
        return base_contribution * confidence_adjustment
    
    def calculate_risk_score(
        self,
        analyzed_clauses: List[ClauseAnalysis]
    ) -> RiskScoreResult:
        """
        Calculate overall contract risk score.
        
        The score is deterministic and computed entirely locally.
        Range: 0-100 (0 = lowest risk, 100 = highest risk)
        
        Args:
            analyzed_clauses: List of analyzed clauses
            
        Returns:
            RiskScoreResult with score, summary, and confidence
        """
        if not analyzed_clauses:
            return RiskScoreResult(
                risk_score=50.0,
                summary="Unable to analyze contract - no clauses identified",
                confidence=0.0,
                breakdown=None
            )
        
        # Count risk levels
        risk_counts = {'high': 0, 'medium': 0, 'low': 0}
        for clause in analyzed_clauses:
            level = clause.risk_level.lower()
            if level in risk_counts:
                risk_counts[level] += 1
        
        # Identify missing clauses
        missing_clauses = self._identify_missing_clauses(analyzed_clauses)
        
        # Count ambiguous clauses
        ambiguous_count = self._count_ambiguous_clauses(analyzed_clauses)
        
        # Calculate raw score
        raw_score = 0.0
        
        # Add contribution from each clause
        for clause in analyzed_clauses:
            raw_score += self._calculate_clause_risk_contribution(clause)
        
        # Add penalty for missing clauses
        raw_score += len(missing_clauses) * self.missing_clause_weight
        
        # Add penalty for ambiguous clauses
        raw_score += ambiguous_count * self.ambiguity_weight
        
        # Normalize to 0-100 scale
        # Use logarithmic normalization to prevent extreme values
        max_possible = (
            len(analyzed_clauses) * self.high_risk_weight * 2.0 +
            len(self.ESSENTIAL_CLAUSES) * self.missing_clause_weight +
            len(analyzed_clauses) * self.ambiguity_weight
        )
        
        if max_possible > 0:
            normalized_score = min(100, (raw_score / max_possible) * 100)
        else:
            normalized_score = 50.0
        
        # Round to 1 decimal
        normalized_score = round(normalized_score, 1)
        
        # Calculate confidence based on analysis quality
        avg_confidence = sum(c.confidence for c in analyzed_clauses) / len(analyzed_clauses)
        coverage = min(1.0, len(analyzed_clauses) / 10)  # Assume 10 clauses is good coverage
        overall_confidence = (avg_confidence * 0.7 + coverage * 0.3)
        
        # Generate summary
        summary = self._generate_summary(
            risk_counts,
            missing_clauses,
            ambiguous_count,
            normalized_score
        )
        
        # Build breakdown
        breakdown = RiskBreakdown(
            high_risk_clauses=risk_counts['high'],
            medium_risk_clauses=risk_counts['medium'],
            low_risk_clauses=risk_counts['low'],
            missing_clauses=missing_clauses,
            ambiguous_clauses=ambiguous_count,
            raw_score=raw_score,
            normalized_score=normalized_score
        )
        
        return RiskScoreResult(
            risk_score=normalized_score,
            summary=summary,
            confidence=round(overall_confidence, 2),
            breakdown={
                'high_risk_clauses': breakdown.high_risk_clauses,
                'medium_risk_clauses': breakdown.medium_risk_clauses,
                'low_risk_clauses': breakdown.low_risk_clauses,
                'missing_clauses': breakdown.missing_clauses,
                'ambiguous_clauses': breakdown.ambiguous_clauses,
                'raw_score': round(breakdown.raw_score, 2),
                'normalized_score': breakdown.normalized_score
            }
        )
    
    def _generate_summary(
        self,
        risk_counts: Dict[str, int],
        missing_clauses: List[str],
        ambiguous_count: int,
        score: float
    ) -> str:
        """Generate human-readable risk summary"""
        parts = []
        
        # Overall assessment
        if score >= 70:
            parts.append("HIGH RISK CONTRACT requiring significant negotiation.")
        elif score >= 40:
            parts.append("MODERATE RISK CONTRACT with areas requiring attention.")
        else:
            parts.append("LOW RISK CONTRACT with generally favorable terms.")
        
        # Specific issues
        if risk_counts['high'] > 0:
            parts.append(f"Contains {risk_counts['high']} high-risk clause(s).")
        
        if missing_clauses:
            parts.append(f"Missing essential clauses: {', '.join(missing_clauses)}.")
        
        if ambiguous_count > 0:
            parts.append(f"{ambiguous_count} clause(s) contain ambiguous language.")
        
        # Recommendation
        if score >= 70:
            parts.append("Recommend detailed legal review and negotiation before signing.")
        elif score >= 40:
            parts.append("Review identified issues with legal counsel.")
        else:
            parts.append("Standard review recommended before execution.")
        
        return " ".join(parts)
    
    def get_priority_items(
        self,
        analyzed_clauses: List[ClauseAnalysis]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get prioritized list of negotiation items.
        
        Returns:
            Dictionary with high/medium/low priority items
        """
        priority = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }
        
        for clause in analyzed_clauses:
            item = {
                'clause_type': clause.type,
                'issue': clause.issue,
                'negotiation': {
                    'objective': clause.negotiation.objective,
                    'reason': clause.negotiation.reason,
                    'suggested_change': clause.negotiation.suggested_change,
                    'leverage': clause.negotiation.leverage
                }
            }
            
            # Determine priority based on risk and leverage
            if clause.risk_level == 'high' or clause.negotiation.leverage == 'high':
                priority['high_priority'].append(item)
            elif clause.risk_level == 'medium' or clause.negotiation.leverage == 'medium':
                priority['medium_priority'].append(item)
            else:
                priority['low_priority'].append(item)
        
        return priority
    
    def compare_with_rag(
        self,
        calculated_risk: str,
        rag_risk: str
    ) -> str:
        """
        Compare calculated risk with RAG-retrieved risk level.
        Returns the more conservative (higher) risk level.
        """
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        
        calc_value = risk_order.get(calculated_risk.lower(), 1)
        rag_value = risk_order.get(rag_risk.lower(), 1)
        
        # Return higher risk (more conservative)
        if rag_value > calc_value:
            return rag_risk.lower()
        return calculated_risk.lower()
