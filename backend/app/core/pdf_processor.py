"""
PDF Processing Pipeline
Handles PDF upload, text extraction, and OCR for scanned documents
"""

import os
import io
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import magic
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import re

from ..config import get_settings

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Production-grade PDF processor with text extraction and OCR support.
    Handles both text-based and scanned PDFs with caching.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = Path(self.settings.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_file(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """
        Validate uploaded file for security.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size = self.settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(file_content) > max_size:
            return False, f"File size exceeds {self.settings.MAX_FILE_SIZE_MB}MB limit"
        
        # Check MIME type using magic bytes
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in self.settings.ALLOWED_MIME_TYPES:
            return False, f"Invalid file type: {mime_type}. Only PDF files are allowed."
        
        # Validate PDF header
        if not file_content[:5] == b'%PDF-':
            return False, "Invalid PDF file format"
        
        # Check filename extension
        if not filename.lower().endswith('.pdf'):
            return False, "File must have .pdf extension"
            
        return True, ""
    
    def get_cache_key(self, file_content: bytes) -> str:
        """Generate cache key from file content hash"""
        return hashlib.sha256(file_content).hexdigest()
    
    def get_cached_text(self, cache_key: str) -> Optional[str]:
        """Retrieve cached extracted text if available"""
        cache_file = self.cache_dir / f"{cache_key}.txt"
        if cache_file.exists():
            logger.info(f"Cache hit for document: {cache_key[:16]}...")
            return cache_file.read_text(encoding='utf-8')
        return None
    
    def save_to_cache(self, cache_key: str, text: str) -> None:
        """Save extracted text to cache"""
        cache_file = self.cache_dir / f"{cache_key}.txt"
        cache_file.write_text(text, encoding='utf-8')
        logger.info(f"Cached document: {cache_key[:16]}...")
    
    def detect_pdf_type(self, file_content: bytes) -> str:
        """
        Detect if PDF is text-based or scanned (image-based).
        
        Returns:
            'text' or 'scanned'
        """
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                total_chars = 0
                pages_checked = min(3, len(pdf.pages))  # Check first 3 pages
                
                for i in range(pages_checked):
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    total_chars += len(text.strip())
                
                # If average chars per page is low, likely scanned
                avg_chars = total_chars / pages_checked if pages_checked > 0 else 0
                
                if avg_chars < 100:
                    logger.info("Detected scanned PDF (low text content)")
                    return 'scanned'
                else:
                    logger.info("Detected text-based PDF")
                    return 'text'
                    
        except Exception as e:
            logger.warning(f"Error detecting PDF type: {e}. Defaulting to text extraction.")
            return 'text'
    
    def extract_text_from_text_pdf(self, file_content: bytes) -> str:
        """Extract text from text-based PDF using pdfplumber"""
        extracted_text = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text.append(f"--- Page {i + 1} ---\n{page_text}")
                    
                    # Also extract tables if present
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = self._format_table(table)
                            extracted_text.append(table_text)
                            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        return "\n\n".join(extracted_text)
    
    def extract_text_from_scanned_pdf(self, file_content: bytes) -> str:
        """Extract text from scanned PDF using Tesseract OCR"""
        extracted_text = []
        
        try:
            # Convert PDF pages to images
            images = convert_from_bytes(file_content, dpi=300)
            
            for i, image in enumerate(images):
                # Preprocess image for better OCR
                processed_image = self._preprocess_image(image)
                
                # Perform OCR
                page_text = pytesseract.image_to_string(
                    processed_image,
                    config='--oem 3 --psm 6'
                )
                
                if page_text.strip():
                    extracted_text.append(f"--- Page {i + 1} ---\n{page_text}")
                    
        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
            raise ValueError(f"Failed to perform OCR on PDF: {str(e)}")
        
        return "\n\n".join(extracted_text)
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast (simple threshold)
        # More advanced preprocessing can be added here
        return image
    
    def _format_table(self, table: list) -> str:
        """Format extracted table as text"""
        if not table:
            return ""
        
        formatted_rows = []
        for row in table:
            if row:
                formatted_row = " | ".join(str(cell) if cell else "" for cell in row)
                formatted_rows.append(formatted_row)
        
        return "\n[TABLE]\n" + "\n".join(formatted_rows) + "\n[/TABLE]"
    
    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        - Remove excessive whitespace
        - Fix common OCR errors
        - Normalize line endings
        - Remove control characters
        """
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove excessive spaces
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Fix common OCR errors
        ocr_corrections = {
            'l1ability': 'liability',
            'tennination': 'termination',
            'confldential': 'confidential',
            '0bligations': 'obligations',
            'indernnity': 'indemnity',
        }
        
        for wrong, correct in ocr_corrections.items():
            text = text.replace(wrong, correct)
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def process(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Main processing pipeline for PDF documents.
        
        Args:
            file_content: Raw PDF bytes
            filename: Original filename
            
        Returns:
            Dictionary with extracted text and metadata
        """
        # Validate file
        is_valid, error = self.validate_file(file_content, filename)
        if not is_valid:
            raise ValueError(error)
        
        # Check cache
        cache_key = self.get_cache_key(file_content)
        cached_text = self.get_cached_text(cache_key)
        
        if cached_text:
            return {
                'document_id': cache_key,
                'filename': filename,
                'text': cached_text,
                'cached': True,
                'pdf_type': 'cached'
            }
        
        # Detect PDF type
        pdf_type = self.detect_pdf_type(file_content)
        
        # Extract text based on type
        if pdf_type == 'scanned':
            raw_text = self.extract_text_from_scanned_pdf(file_content)
        else:
            raw_text = self.extract_text_from_text_pdf(file_content)
        
        # Normalize text
        normalized_text = self.normalize_text(raw_text)
        
        if not normalized_text:
            raise ValueError("No text could be extracted from the PDF")
        
        # Cache the result
        self.save_to_cache(cache_key, normalized_text)
        
        return {
            'document_id': cache_key,
            'filename': filename,
            'text': normalized_text,
            'cached': False,
            'pdf_type': pdf_type,
            'char_count': len(normalized_text),
            'word_count': len(normalized_text.split())
        }
