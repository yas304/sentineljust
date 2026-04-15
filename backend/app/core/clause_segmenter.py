"""
Clause Segmentation Engine
Segments contract text into individual clauses using rule-based and NLP methods
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import spacy
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Clause:
    """Represents a segmented clause"""
    id: str
    text: str
    heading: Optional[str]
    section_number: Optional[str]
    start_position: int
    end_position: int
    

class ClauseSegmenter:
    """
    Production-grade clause segmenter using hybrid approach:
    1. Rule-based splitting (headings, numbering patterns)
    2. NLP refinement using spaCy
    """
    
    def __init__(self):
        # Load spaCy model for NLP processing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Downloading en_core_web_sm...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
        
        # Patterns for identifying clause boundaries
        self.section_patterns = [
            # Numbered sections: 1. or 1) or (1) or 1:
            r'^[\s]*(\d+(?:\.\d+)*)[.):]\s+([A-Z][^.]*)',
            # Lettered sections: a. or a) or (a)
            r'^[\s]*([a-z])[.):]\s+([A-Z][^.]*)',
            # Roman numerals: i. or I. or (i)
            r'^[\s]*((?:[ivxIVX]+))[.):]\s+([A-Z][^.]*)',
            # Article/Section headers
            r'^[\s]*(ARTICLE|SECTION|CLAUSE|PART)\s+(\d+|[IVXLCDM]+)[.:]\s*(.*)',
            # All caps headers
            r'^[\s]*([A-Z][A-Z\s]{3,}[A-Z])[\s]*$',
        ]
        
        # Keywords indicating clause starts
        self.clause_start_keywords = [
            'shall', 'must', 'agrees to', 'covenants', 'represents', 
            'warrants', 'acknowledges', 'understands', 'hereby',
            'notwithstanding', 'provided that', 'subject to',
            'in the event', 'in consideration of'
        ]
        
        # Minimum clause length (characters)
        self.min_clause_length = 50
        
        # Maximum clause length (characters)
        self.max_clause_length = 5000
        
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better segmentation"""
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Ensure proper spacing after periods
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        
        # Remove page markers
        text = re.sub(r'---\s*Page\s+\d+\s*---', '\n', text)
        
        return text
    
    def _find_section_boundaries(self, text: str) -> List[Tuple[int, str, str]]:
        """
        Find section boundaries using regex patterns.
        
        Returns:
            List of tuples: (position, section_number, heading)
        """
        boundaries = []
        
        for pattern in self.section_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                pos = match.start()
                groups = match.groups()
                
                if len(groups) >= 2:
                    section_num = groups[0]
                    heading = groups[1] if len(groups) > 1 else ""
                else:
                    section_num = ""
                    heading = groups[0] if groups else ""
                
                boundaries.append((pos, section_num, heading.strip()))
        
        # Sort by position
        boundaries.sort(key=lambda x: x[0])
        
        # Remove duplicates (same position)
        unique_boundaries = []
        seen_positions = set()
        for b in boundaries:
            if b[0] not in seen_positions:
                unique_boundaries.append(b)
                seen_positions.add(b[0])
        
        return unique_boundaries
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split on double newlines or single newlines followed by indent
        paragraphs = re.split(r'\n\s*\n|\n(?=\s{4,})', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _merge_short_segments(self, segments: List[str]) -> List[str]:
        """Merge segments that are too short"""
        merged = []
        current = ""
        
        for segment in segments:
            if len(current) + len(segment) < self.min_clause_length:
                current = f"{current}\n{segment}".strip() if current else segment
            else:
                if current:
                    merged.append(current)
                current = segment
        
        if current:
            merged.append(current)
            
        return merged
    
    def _split_long_segments(self, segments: List[str]) -> List[str]:
        """Split segments that are too long using sentence boundaries"""
        result = []
        
        for segment in segments:
            if len(segment) <= self.max_clause_length:
                result.append(segment)
            else:
                # Use NLP to find sentence boundaries
                doc = self.nlp(segment)
                current_chunk = ""
                
                for sent in doc.sents:
                    sent_text = sent.text.strip()
                    
                    if len(current_chunk) + len(sent_text) < self.max_clause_length:
                        current_chunk = f"{current_chunk} {sent_text}".strip()
                    else:
                        if current_chunk:
                            result.append(current_chunk)
                        current_chunk = sent_text
                
                if current_chunk:
                    result.append(current_chunk)
        
        return result
    
    def _refine_with_nlp(self, segments: List[str]) -> List[str]:
        """Use NLP to refine clause boundaries"""
        refined = []
        
        for segment in segments:
            # Skip very short segments
            if len(segment) < 20:
                continue
                
            # Check if segment starts with a clause keyword
            segment_lower = segment.lower()
            starts_with_keyword = any(
                segment_lower.startswith(kw) or f" {kw}" in segment_lower[:50]
                for kw in self.clause_start_keywords
            )
            
            # Use spaCy for sentence analysis
            doc = self.nlp(segment[:1000])  # Limit processing for performance
            
            # Check if this looks like a complete clause
            has_verb = any(token.pos_ == "VERB" for token in doc)
            has_subject = any(token.dep_ in ("nsubj", "nsubjpass") for token in doc)
            
            if has_verb or has_subject or starts_with_keyword:
                refined.append(segment)
            elif refined:
                # Merge with previous if not a complete clause
                refined[-1] = f"{refined[-1]}\n{segment}"
            else:
                refined.append(segment)
        
        return refined
    
    def _extract_heading(self, text: str) -> Tuple[Optional[str], str]:
        """Extract heading from clause text if present"""
        lines = text.split('\n')
        
        if not lines:
            return None, text
        
        first_line = lines[0].strip()
        
        # Check if first line is a heading (all caps or short with caps)
        if (first_line.isupper() and len(first_line) < 100) or \
           re.match(r'^[\d.]+\s+[A-Z][^.]*$', first_line):
            heading = first_line
            body = '\n'.join(lines[1:]).strip()
            return heading, body if body else text
        
        return None, text
    
    def _extract_section_number(self, text: str) -> Tuple[Optional[str], str]:
        """Extract section number from clause text"""
        # Match common section number patterns
        patterns = [
            r'^(\d+(?:\.\d+)*)[.):\s]+',
            r'^([a-z])[.):\s]+',
            r'^((?:ARTICLE|SECTION|CLAUSE)\s+\d+)[.:]\s*',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                section_num = match.group(1)
                remaining = text[match.end():].strip()
                return section_num, remaining
        
        return None, text
    
    def segment(self, text: str) -> List[Clause]:
        """
        Main segmentation method.
        
        Args:
            text: Full contract text
            
        Returns:
            List of Clause objects
        """
        logger.info("Starting clause segmentation...")
        
        # Preprocess
        text = self._preprocess_text(text)
        
        # Find section boundaries
        boundaries = self._find_section_boundaries(text)
        
        # If we found clear boundaries, use them
        if len(boundaries) >= 3:
            segments = self._segment_by_boundaries(text, boundaries)
        else:
            # Fall back to paragraph-based splitting
            segments = self._split_by_paragraphs(text)
        
        # Merge short segments
        segments = self._merge_short_segments(segments)
        
        # Split long segments
        segments = self._split_long_segments(segments)
        
        # Refine with NLP
        segments = self._refine_with_nlp(segments)
        
        # Create Clause objects
        clauses = []
        position = 0
        
        for i, segment in enumerate(segments):
            if not segment.strip():
                continue
                
            # Find actual position in text
            seg_pos = text.find(segment[:50], position)
            if seg_pos == -1:
                seg_pos = position
            
            # Extract heading and section number
            heading, body = self._extract_heading(segment)
            section_num, body = self._extract_section_number(body if body != segment else segment)
            
            clause = Clause(
                id=f"clause_{i+1:03d}",
                text=segment,
                heading=heading,
                section_number=section_num,
                start_position=seg_pos,
                end_position=seg_pos + len(segment)
            )
            clauses.append(clause)
            position = seg_pos + len(segment)
        
        logger.info(f"Segmented into {len(clauses)} clauses")
        return clauses
    
    def _segment_by_boundaries(self, text: str, boundaries: List[Tuple[int, str, str]]) -> List[str]:
        """Segment text using identified boundaries"""
        segments = []
        
        for i, (pos, section_num, heading) in enumerate(boundaries):
            # Get end position (start of next boundary or end of text)
            end_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            
            segment = text[pos:end_pos].strip()
            if segment:
                segments.append(segment)
        
        # Also include any text before the first boundary
        if boundaries and boundaries[0][0] > 0:
            preamble = text[:boundaries[0][0]].strip()
            if preamble and len(preamble) > self.min_clause_length:
                segments.insert(0, preamble)
        
        return segments
    
    def get_clause_context(self, clauses: List[Clause], clause_index: int, context_size: int = 1) -> str:
        """
        Get surrounding context for a clause.
        
        Args:
            clauses: List of all clauses
            clause_index: Index of target clause
            context_size: Number of clauses before/after to include
            
        Returns:
            Context string
        """
        start_idx = max(0, clause_index - context_size)
        end_idx = min(len(clauses), clause_index + context_size + 1)
        
        context_parts = []
        for i in range(start_idx, end_idx):
            if i == clause_index:
                context_parts.append(f"[CURRENT CLAUSE]\n{clauses[i].text}\n[/CURRENT CLAUSE]")
            else:
                context_parts.append(f"[CONTEXT]\n{clauses[i].text[:500]}...\n[/CONTEXT]")
        
        return "\n\n".join(context_parts)
