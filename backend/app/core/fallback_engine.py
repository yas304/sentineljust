"""
Fallback Analysis Engine
Local deterministic engine for when Gemini API fails
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher

from ..config import CLAUSE_KEYWORDS, RISK_INDICATORS, CLAUSE_TYPES
from ..models.schemas import ClauseAnalysis, NegotiationStrategy

logger = logging.getLogger(__name__)


# Template-based negotiation strategies
NEGOTIATION_TEMPLATES = {
    "termination": {
        "short_notice": {
            "objective": "Extend termination notice period",
            "reason": "Short notice period creates operational continuity risk",
            "suggested_change": "Extend notice period to minimum 60 days",
            "leverage": "medium"
        },
        "without_cause": {
            "objective": "Add termination restrictions",
            "reason": "Unrestricted termination creates business uncertainty",
            "suggested_change": "Require material breach or add cure period",
            "leverage": "high"
        },
        "default": {
            "objective": "Ensure balanced termination rights",
            "reason": "Termination provisions affect contract stability",
            "suggested_change": "Ensure mutual termination rights with adequate notice",
            "leverage": "medium"
        }
    },
    "liability": {
        "unlimited": {
            "objective": "Cap liability exposure",
            "reason": "Unlimited liability creates unacceptable financial risk",
            "suggested_change": "Add liability cap tied to contract value or insurance limits",
            "leverage": "high"
        },
        "one_sided": {
            "objective": "Balance liability provisions",
            "reason": "One-sided liability allocation is inequitable",
            "suggested_change": "Ensure mutual liability limitations apply",
            "leverage": "high"
        },
        "default": {
            "objective": "Review liability allocation",
            "reason": "Liability terms directly impact risk exposure",
            "suggested_change": "Verify liability limits are proportionate to contract scope",
            "leverage": "medium"
        }
    },
    "indemnification": {
        "broad": {
            "objective": "Narrow indemnification scope",
            "reason": "Overly broad indemnification creates unlimited exposure",
            "suggested_change": "Limit to direct damages from breach or negligence",
            "leverage": "high"
        },
        "one_sided": {
            "objective": "Add mutual indemnification",
            "reason": "One-sided indemnification is commercially unreasonable",
            "suggested_change": "Include reciprocal indemnification obligations",
            "leverage": "high"
        },
        "default": {
            "objective": "Clarify indemnification triggers",
            "reason": "Clear indemnification terms prevent disputes",
            "suggested_change": "Specify indemnifiable events and process clearly",
            "leverage": "medium"
        }
    },
    "confidentiality": {
        "perpetual": {
            "objective": "Add time limitation to confidentiality",
            "reason": "Perpetual obligations are difficult to manage",
            "suggested_change": "Limit confidentiality period to 3-5 years post-term",
            "leverage": "medium"
        },
        "broad_definition": {
            "objective": "Narrow confidential information definition",
            "reason": "Overly broad definitions create compliance burden",
            "suggested_change": "Require marking or written designation of confidential info",
            "leverage": "medium"
        },
        "default": {
            "objective": "Ensure reasonable confidentiality terms",
            "reason": "Balanced confidentiality protects both parties",
            "suggested_change": "Add standard exceptions (public info, independent development)",
            "leverage": "low"
        }
    },
    "intellectual_property": {
        "broad_license": {
            "objective": "Limit IP license scope",
            "reason": "Broad IP grants may affect core business assets",
            "suggested_change": "Restrict license to specific use cases and term",
            "leverage": "high"
        },
        "ownership_transfer": {
            "objective": "Retain IP ownership where appropriate",
            "reason": "IP ownership affects competitive position",
            "suggested_change": "Grant license instead of ownership transfer",
            "leverage": "high"
        },
        "default": {
            "objective": "Clarify IP rights",
            "reason": "Clear IP allocation prevents future disputes",
            "suggested_change": "Explicitly define ownership of pre-existing and developed IP",
            "leverage": "medium"
        }
    },
    "payment": {
        "unfavorable_terms": {
            "objective": "Improve payment terms",
            "reason": "Payment terms affect cash flow and working capital",
            "suggested_change": "Negotiate net 30-45 day payment terms",
            "leverage": "medium"
        },
        "penalties": {
            "objective": "Remove or limit late payment penalties",
            "reason": "Excessive penalties create financial risk",
            "suggested_change": "Cap penalties at reasonable interest rate",
            "leverage": "medium"
        },
        "default": {
            "objective": "Clarify payment terms",
            "reason": "Clear payment terms prevent disputes",
            "suggested_change": "Specify invoice process and payment timeline",
            "leverage": "low"
        }
    },
    "warranty": {
        "no_warranty": {
            "objective": "Add basic warranties",
            "reason": "Lack of warranties creates quality and performance risk",
            "suggested_change": "Include warranties for merchantability and fitness",
            "leverage": "high"
        },
        "limited": {
            "objective": "Extend warranty coverage",
            "reason": "Limited warranties may not adequately protect interests",
            "suggested_change": "Extend warranty period and scope of coverage",
            "leverage": "medium"
        },
        "default": {
            "objective": "Review warranty scope",
            "reason": "Warranties allocate risk for product/service quality",
            "suggested_change": "Ensure warranties cover key performance requirements",
            "leverage": "medium"
        }
    },
    "force_majeure": {
        "narrow": {
            "objective": "Expand force majeure events",
            "reason": "Narrow force majeure limits protection from unforeseen events",
            "suggested_change": "Include pandemic, cyber attacks, and supply chain disruption",
            "leverage": "medium"
        },
        "one_sided": {
            "objective": "Ensure mutual force majeure protection",
            "reason": "One-sided protection is inequitable",
            "suggested_change": "Apply force majeure provisions to both parties",
            "leverage": "medium"
        },
        "default": {
            "objective": "Review force majeure coverage",
            "reason": "Force majeure addresses uncontrollable events",
            "suggested_change": "Verify coverage of relevant risk scenarios",
            "leverage": "low"
        }
    },
    "default": {
        "default": {
            "objective": "Review clause terms",
            "reason": "All contract terms should be carefully evaluated",
            "suggested_change": "Ensure terms align with business requirements",
            "leverage": "low"
        }
    }
}


# Issue templates
ISSUE_TEMPLATES = {
    "termination": {
        "high": "Unfavorable termination provisions with inadequate notice or unrestricted rights",
        "medium": "Termination terms may require negotiation for better balance",
        "low": "Standard termination provisions with reasonable notice periods"
    },
    "liability": {
        "high": "Unlimited or significantly imbalanced liability allocation",
        "medium": "Liability provisions may benefit from additional protections",
        "low": "Reasonable liability limitations in place"
    },
    "indemnification": {
        "high": "Broad indemnification obligations creating significant exposure",
        "medium": "Indemnification scope may be overly broad",
        "low": "Standard mutual indemnification provisions"
    },
    "default": {
        "high": "Clause contains terms requiring immediate attention and negotiation",
        "medium": "Clause terms should be reviewed for potential improvements",
        "low": "Clause appears standard with minimal risk"
    }
}


# Suggestion templates
SUGGESTION_TEMPLATES = {
    "termination": {
        "high": "Negotiate for mutual termination rights with minimum 60-day notice and cure period for material breach",
        "medium": "Consider extending notice period and adding specific termination triggers",
        "low": "Review and confirm alignment with business requirements"
    },
    "liability": {
        "high": "Add liability cap proportionate to contract value and exclude consequential damages",
        "medium": "Verify liability limitations are mutual and appropriately scoped",
        "low": "Confirm liability allocation aligns with insurance coverage"
    },
    "indemnification": {
        "high": "Narrow scope to direct claims from material breach, add caps, require mutual obligations",
        "medium": "Clarify triggering events and add procedural requirements for claims",
        "low": "Verify indemnification aligns with liability provisions"
    },
    "default": {
        "high": "Conduct detailed legal review and negotiate improved terms",
        "medium": "Review with legal counsel and consider requesting modifications",
        "low": "Standard clause requiring no immediate action"
    }
}


class FallbackEngine:
    """
    Deterministic fallback engine for clause analysis when Gemini fails.
    Uses semantic similarity, rule-based classification, and templates.
    """
    
    def __init__(self):
        self.keyword_patterns = self._compile_keyword_patterns()
        self.risk_patterns = self._compile_risk_patterns()
    
    def _compile_keyword_patterns(self) -> Dict[str, re.Pattern]:
        """Compile keyword patterns for clause classification"""
        patterns = {}
        for clause_type, keywords in CLAUSE_KEYWORDS.items():
            pattern = '|'.join(re.escape(kw) for kw in keywords)
            patterns[clause_type] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def _compile_risk_patterns(self) -> Dict[str, re.Pattern]:
        """Compile risk indicator patterns"""
        patterns = {}
        for risk_level, indicators in RISK_INDICATORS.items():
            pattern = '|'.join(re.escape(ind) for ind in indicators)
            patterns[risk_level] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def classify_clause(self, clause_text: str) -> Tuple[str, float]:
        """
        Classify clause type using keyword matching.
        
        Returns:
            Tuple of (clause_type, confidence)
        """
        clause_lower = clause_text.lower()
        scores = {}
        
        for clause_type, pattern in self.keyword_patterns.items():
            matches = pattern.findall(clause_lower)
            if matches:
                # Weight by number of matches and their specificity
                scores[clause_type] = len(matches) * (1 + len(set(matches)) * 0.5)
        
        if not scores:
            return "unknown", 0.3
        
        # Get highest scoring type
        best_type = max(scores, key=scores.get)
        
        # Calculate confidence based on match strength
        max_score = scores[best_type]
        confidence = min(0.8, 0.4 + (max_score * 0.1))
        
        return best_type, confidence
    
    def assess_risk(self, clause_text: str, clause_type: str) -> Tuple[str, List[str]]:
        """
        Assess risk level using heuristic analysis.
        
        Returns:
            Tuple of (risk_level, identified_risk_factors)
        """
        clause_lower = clause_text.lower()
        risk_factors = []
        
        # Check for high-risk indicators
        high_matches = self.risk_patterns['high'].findall(clause_lower)
        if high_matches:
            risk_factors.extend([f"Contains '{m}'" for m in set(high_matches)])
        
        # Check for medium-risk indicators
        medium_matches = self.risk_patterns['medium'].findall(clause_lower)
        
        # Check for low-risk (protective) indicators
        low_matches = self.risk_patterns['low'].findall(clause_lower)
        
        # Heuristic risk rules
        # Short notice period
        notice_match = re.search(r'(\d+)\s*(?:days?|business days?)\s*(?:notice|prior)', clause_lower)
        if notice_match:
            days = int(notice_match.group(1))
            if days < 30:
                risk_factors.append(f"Short notice period ({days} days)")
        
        # Missing key terms
        if clause_type == 'termination' and 'cure' not in clause_lower and 'remedy' not in clause_lower:
            risk_factors.append("No cure period specified")
        
        if clause_type == 'liability' and 'cap' not in clause_lower and 'limit' not in clause_lower:
            risk_factors.append("No liability cap specified")
        
        # Vague language
        vague_terms = ['reasonable', 'best efforts', 'may', 'as appropriate', 'generally']
        vague_count = sum(1 for term in vague_terms if term in clause_lower)
        if vague_count >= 3:
            risk_factors.append("Contains multiple vague terms")
        
        # Calculate risk level
        if len(high_matches) >= 2 or len(risk_factors) >= 3:
            return 'high', risk_factors
        elif len(high_matches) >= 1 or len(medium_matches) >= 2 or len(risk_factors) >= 2:
            return 'medium', risk_factors
        elif len(low_matches) >= 2:
            return 'low', risk_factors
        else:
            return 'medium', risk_factors  # Default to medium when uncertain
    
    def get_negotiation_strategy(
        self, 
        clause_type: str, 
        risk_level: str,
        risk_factors: List[str]
    ) -> NegotiationStrategy:
        """
        Get negotiation strategy from templates.
        """
        # Determine specific scenario
        scenario = "default"
        
        risk_text = ' '.join(risk_factors).lower()
        
        if clause_type == "termination":
            if "short notice" in risk_text:
                scenario = "short_notice"
            elif "without cause" in risk_text or "unrestricted" in risk_text:
                scenario = "without_cause"
        elif clause_type == "liability":
            if "no liability cap" in risk_text or "unlimited" in risk_text:
                scenario = "unlimited"
            elif "one-sided" in risk_text:
                scenario = "one_sided"
        elif clause_type == "indemnification":
            if "broad" in risk_text or "unlimited" in risk_text:
                scenario = "broad"
        
        # Get template
        type_templates = NEGOTIATION_TEMPLATES.get(clause_type, NEGOTIATION_TEMPLATES["default"])
        template = type_templates.get(scenario, type_templates["default"])
        
        # Adjust leverage based on risk level
        leverage = template["leverage"]
        if risk_level == "high" and leverage == "low":
            leverage = "medium"
        
        return NegotiationStrategy(
            objective=template["objective"],
            reason=template["reason"],
            suggested_change=template["suggested_change"],
            leverage=leverage
        )
    
    def get_issue_description(self, clause_type: str, risk_level: str, risk_factors: List[str]) -> str:
        """Get issue description from templates"""
        type_issues = ISSUE_TEMPLATES.get(clause_type, ISSUE_TEMPLATES["default"])
        base_issue = type_issues.get(risk_level, type_issues["medium"])
        
        if risk_factors:
            return f"{base_issue}. Specific concerns: {'; '.join(risk_factors[:3])}"
        return base_issue
    
    def get_suggestion(self, clause_type: str, risk_level: str) -> str:
        """Get suggestion from templates"""
        type_suggestions = SUGGESTION_TEMPLATES.get(clause_type, SUGGESTION_TEMPLATES["default"])
        return type_suggestions.get(risk_level, type_suggestions["medium"])
    
    def analyze_with_rag_context(
        self, 
        clause_text: str,
        retrieved_clauses: List[Dict[str, Any]]
    ) -> ClauseAnalysis:
        """
        Analyze clause using RAG context for improved accuracy.
        """
        # If we have similar clauses, use them to inform analysis
        if retrieved_clauses:
            # Get most common type from similar clauses
            type_counts = {}
            risk_counts = {}
            
            for rc in retrieved_clauses:
                ct = rc.get('clause_type', 'unknown')
                rl = rc.get('risk_level', 'medium')
                type_counts[ct] = type_counts.get(ct, 0) + 1
                risk_counts[rl] = risk_counts.get(rl, 0) + 1
            
            # Use most common as guidance
            rag_type = max(type_counts, key=type_counts.get) if type_counts else None
            rag_risk = max(risk_counts, key=risk_counts.get) if risk_counts else None
            
            # Get issue and recommendation from best matching clause
            best_match = retrieved_clauses[0]
            rag_issue = best_match.get('issue', '')
            rag_recommendation = best_match.get('recommendation', '')
            rag_negotiation_hint = best_match.get('negotiation_hint', '')
            
            # Classify locally
            local_type, type_confidence = self.classify_clause(clause_text)
            local_risk, risk_factors = self.assess_risk(clause_text, local_type)
            
            # Reconcile with RAG data
            if rag_type and rag_type != 'unknown':
                final_type = rag_type if type_confidence < 0.6 else local_type
            else:
                final_type = local_type
            
            if rag_risk:
                # Prefer higher risk assessment for safety
                risk_order = {'low': 0, 'medium': 1, 'high': 2}
                final_risk = rag_risk if risk_order.get(rag_risk, 1) > risk_order.get(local_risk, 1) else local_risk
            else:
                final_risk = local_risk
            
            # Build issue description
            if rag_issue:
                issue = rag_issue
            else:
                issue = self.get_issue_description(final_type, final_risk, risk_factors)
            
            # Build suggestion
            if rag_recommendation:
                suggestion = rag_recommendation
            else:
                suggestion = self.get_suggestion(final_type, final_risk)
            
            # Build negotiation strategy
            negotiation = self.get_negotiation_strategy(final_type, final_risk, risk_factors)
            
            # Incorporate RAG negotiation hint if available
            if rag_negotiation_hint:
                negotiation.suggested_change = rag_negotiation_hint
            
            confidence = max(0.6, type_confidence)
            
        else:
            # Pure local analysis
            final_type, type_confidence = self.classify_clause(clause_text)
            final_risk, risk_factors = self.assess_risk(clause_text, final_type)
            issue = self.get_issue_description(final_type, final_risk, risk_factors)
            suggestion = self.get_suggestion(final_type, final_risk)
            negotiation = self.get_negotiation_strategy(final_type, final_risk, risk_factors)
            confidence = type_confidence * 0.8  # Lower confidence without RAG
        
        return ClauseAnalysis(
            text=clause_text,
            type=final_type,
            risk_level=final_risk,
            issue=issue,
            suggestion=suggestion,
            negotiation=negotiation,
            confidence=confidence,
            source="fallback"
        )
    
    def analyze_clause(
        self, 
        clause_text: str,
        retrieved_clauses: List[Dict[str, Any]] = None
    ) -> ClauseAnalysis:
        """
        Main entry point for fallback clause analysis.
        """
        if retrieved_clauses:
            return self.analyze_with_rag_context(clause_text, retrieved_clauses)
        
        # Pure heuristic analysis
        clause_type, confidence = self.classify_clause(clause_text)
        risk_level, risk_factors = self.assess_risk(clause_text, clause_type)
        
        return ClauseAnalysis(
            text=clause_text,
            type=clause_type,
            risk_level=risk_level,
            issue=self.get_issue_description(clause_type, risk_level, risk_factors),
            suggestion=self.get_suggestion(clause_type, risk_level),
            negotiation=self.get_negotiation_strategy(clause_type, risk_level, risk_factors),
            confidence=confidence * 0.7,
            source="fallback"
        )
