"""
Gemini Integration Engine
Primary AI engine for clause analysis using Google's Gemini API
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import get_settings
from ..models.schemas import ClauseAnalysis, NegotiationStrategy, GeminiResponse

logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors"""
    pass


class GeminiTimeoutError(GeminiAPIError):
    """Timeout error for Gemini API"""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Rate limit error for Gemini API"""
    pass


class GeminiInvalidResponseError(GeminiAPIError):
    """Invalid response from Gemini API"""
    pass


class GeminiEngine:
    """
    Production-grade Gemini integration for contract analysis.
    Handles clause classification, risk detection, and negotiation strategies.
    """
    
    # System prompt for contract analysis
    SYSTEM_PROMPT = """You are a contract intelligence engine. You MUST return strict JSON only. No explanations outside JSON.

You are an expert legal analyst specializing in contract review, risk assessment, and negotiation strategy. Your analysis must be:
- Precise and legally accurate
- Actionable with specific recommendations
- Risk-aware with clear justifications
- Strategic in negotiation advice

Never provide legal advice - only analysis and recommendations for discussion with legal counsel."""

    # User prompt template
    USER_PROMPT_TEMPLATE = """Clause:
{clause_text}

Context from similar clauses:
{retrieved_clauses}

Tasks:
1. Identify clause type
2. Assign risk level (low/medium/high)
3. Identify issue
4. Suggest improvement
5. Generate negotiation strategy:
   - objective
   - reason
   - suggested_change
   - leverage (low/medium/high)

Return JSON:
{{
  "type": "...",
  "risk_level": "...",
  "issue": "...",
  "suggestion": "...",
  "negotiation": {{
    "objective": "...",
    "reason": "...",
    "suggested_change": "...",
    "leverage": "..."
  }}
}}"""

    def __init__(self):
        self.settings = get_settings()
        
        # Configure Gemini API
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0.1,  # Low temperature for consistent outputs
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        
        self.timeout = self.settings.GEMINI_TIMEOUT
        self.retry_count = self.settings.GEMINI_RETRY_COUNT
        
    def _format_retrieved_clauses(self, retrieved_clauses: List[Dict[str, Any]]) -> str:
        """Format retrieved clauses for context"""
        if not retrieved_clauses:
            return "No similar clauses found in database."
        
        formatted = []
        for i, clause in enumerate(retrieved_clauses[:3], 1):  # Limit to top 3
            formatted.append(f"""
Example {i}:
- Type: {clause.get('clause_type', 'unknown')}
- Risk: {clause.get('risk_level', 'unknown')}
- Issue: {clause.get('issue', 'N/A')}
- Recommendation: {clause.get('recommendation', 'N/A')}
- Negotiation hint: {clause.get('negotiation_hint', 'N/A')}
""")
        
        return "\n".join(formatted)
    
    def _build_prompt(self, clause_text: str, retrieved_clauses: List[Dict[str, Any]]) -> str:
        """Build the analysis prompt"""
        context = self._format_retrieved_clauses(retrieved_clauses)
        
        return self.USER_PROMPT_TEMPLATE.format(
            clause_text=clause_text[:2000],  # Limit clause length
            retrieved_clauses=context
        )
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Gemini response"""
        # Clean response
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise GeminiInvalidResponseError(f"Invalid JSON response: {str(e)}")
        
        # Validate using Pydantic model
        try:
            validated = GeminiResponse(**data)
            return validated.model_dump()
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            raise GeminiInvalidResponseError(f"Response validation failed: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((GeminiTimeoutError, GeminiRateLimitError))
    )
    async def _call_gemini_api(self, prompt: str) -> str:
        """Make API call to Gemini with retry logic"""
        try:
            # Create chat with system prompt
            chat = self.model.start_chat(history=[])
            
            # Set up timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    chat.send_message,
                    f"{self.SYSTEM_PROMPT}\n\n{prompt}"
                ),
                timeout=self.timeout
            )
            
            if not response or not response.text:
                raise GeminiInvalidResponseError("Empty response from Gemini API")
            
            return response.text
            
        except asyncio.TimeoutError:
            logger.warning(f"Gemini API timeout after {self.timeout}s")
            raise GeminiTimeoutError(f"API timeout after {self.timeout} seconds")
            
        except Exception as e:
            error_str = str(e).lower()
            
            if 'rate limit' in error_str or '429' in error_str:
                logger.warning("Gemini API rate limit hit")
                raise GeminiRateLimitError("Rate limit exceeded")
            
            if 'timeout' in error_str:
                raise GeminiTimeoutError(str(e))
            
            logger.error(f"Gemini API error: {e}")
            raise GeminiAPIError(str(e))
    
    async def analyze_clause(
        self, 
        clause_text: str,
        retrieved_clauses: List[Dict[str, Any]] = None
    ) -> Optional[ClauseAnalysis]:
        """
        Analyze a single clause using Gemini.
        
        Args:
            clause_text: The clause text to analyze
            retrieved_clauses: Similar clauses from RAG pipeline
            
        Returns:
            ClauseAnalysis object or None if analysis fails
        """
        if not clause_text or len(clause_text.strip()) < 20:
            logger.warning("Clause too short for analysis")
            return None
        
        retrieved_clauses = retrieved_clauses or []
        
        try:
            # Build prompt
            prompt = self._build_prompt(clause_text, retrieved_clauses)
            
            # Call API
            response_text = await self._call_gemini_api(prompt)
            
            # Parse response
            parsed = self._parse_response(response_text)
            
            # Create ClauseAnalysis object
            negotiation = NegotiationStrategy(
                objective=parsed['negotiation']['objective'],
                reason=parsed['negotiation']['reason'],
                suggested_change=parsed['negotiation']['suggested_change'],
                leverage=parsed['negotiation']['leverage'].lower()
            )
            
            analysis = ClauseAnalysis(
                text=clause_text,
                type=parsed['type'],
                risk_level=parsed['risk_level'].lower(),
                issue=parsed['issue'],
                suggestion=parsed['suggestion'],
                negotiation=negotiation,
                confidence=0.85,  # High confidence for Gemini
                source="gemini"
            )
            
            return analysis
            
        except GeminiAPIError as e:
            logger.error(f"Gemini analysis failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in clause analysis: {e}")
            return None
    
    async def analyze_clauses_batch(
        self,
        clauses: List[Dict[str, Any]],
        retrieved_clauses_map: Dict[str, List[Dict[str, Any]]] = None
    ) -> List[Optional[ClauseAnalysis]]:
        """
        Analyze multiple clauses in batch.
        
        Args:
            clauses: List of clause dictionaries with 'id' and 'text'
            retrieved_clauses_map: Map of clause_id to retrieved similar clauses
            
        Returns:
            List of ClauseAnalysis objects (may contain None for failed analyses)
        """
        retrieved_clauses_map = retrieved_clauses_map or {}
        
        # Process clauses concurrently with semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def analyze_with_semaphore(clause):
            async with semaphore:
                clause_id = clause.get('id', '')
                retrieved = retrieved_clauses_map.get(clause_id, [])
                return await self.analyze_clause(clause['text'], retrieved)
        
        tasks = [analyze_with_semaphore(clause) for clause in clauses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch analysis error: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def generate_document_summary(self, clauses: List[ClauseAnalysis]) -> str:
        """
        Generate an overall document risk summary using Gemini.
        
        Args:
            clauses: List of analyzed clauses
            
        Returns:
            Summary string
        """
        if not clauses:
            return "No clauses analyzed."
        
        # Build summary prompt
        clause_summaries = []
        for i, clause in enumerate(clauses[:15], 1):  # Limit for prompt size
            clause_summaries.append(
                f"{i}. Type: {clause.type}, Risk: {clause.risk_level}, Issue: {clause.issue[:100]}"
            )
        
        prompt = f"""Based on the following clause analysis summary, provide a concise overall risk assessment for this contract (2-3 sentences max):

{chr(10).join(clause_summaries)}

Return only the summary text, no JSON."""

        try:
            response = await self._call_gemini_api(prompt)
            return response.strip()
        except GeminiAPIError:
            return self._generate_local_summary(clauses)
    
    def _generate_local_summary(self, clauses: List[ClauseAnalysis]) -> str:
        """Generate summary locally when Gemini fails"""
        high_risk = sum(1 for c in clauses if c.risk_level == 'high')
        medium_risk = sum(1 for c in clauses if c.risk_level == 'medium')
        
        if high_risk > 3:
            return f"This contract contains {high_risk} high-risk clauses requiring immediate attention. Careful review and negotiation is strongly recommended before signing."
        elif high_risk > 0:
            return f"This contract contains {high_risk} high-risk and {medium_risk} medium-risk clauses. Key areas include termination, liability, and indemnification provisions."
        else:
            return f"This contract appears relatively balanced with {medium_risk} medium-risk clauses. Standard review process recommended."
