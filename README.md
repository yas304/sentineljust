# Sentinel Core

## AI-Powered Contract Intelligence and Negotiation System

Sentinel Core is a production-grade platform that analyzes PDF contracts and generates structured, actionable legal insights with negotiation strategies.

![Sentinel Core](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

### Core Capabilities
- **PDF Processing**: Handles both text-based and scanned PDFs (OCR)
- **Clause Segmentation**: Rule-based and NLP-powered clause extraction
- **AI Analysis**: Gemini-powered clause classification and risk detection
- **Negotiation Strategies**: Actionable negotiation recommendations
- **Risk Scoring**: Deterministic contract risk scoring (0-100)
- **RAG Pipeline**: Context-aware analysis using similar clauses

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (HTML/JS)                      │
├─────────────────────────────────────────────────────────────┤
│                     FastAPI Backend                          │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ PDF Processor│Clause Segmenter│Gemini Engine│Fallback Engine│
├─────────────┴─────────────┴─────────────┴──────────────────┤
│                     RAG Pipeline (pgvector)                  │
├─────────────────────────────────────────────────────────────┤
│                    Supabase (PostgreSQL)                     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Tesseract OCR (for scanned PDFs)
- Poppler (for PDF to image conversion)

### Installation

1. **Clone the repository**
```bash
cd "c:\Users\yashw\Downloads\sentinel legal"
```

2. **Create virtual environment**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

4. **Configure environment**
```bash
# Edit .env file with your API keys (already configured)
```

5. **Setup Supabase database**
```bash
# Run the SQL from supabase_setup.sql in your Supabase SQL editor
```

6. **Load initial dataset**
```bash
# This will be done via API after starting the server
```

7. **Start the server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Open the application**
```
http://localhost:8000
```

## API Documentation

### Endpoints

#### Upload Document
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file: <PDF file>
```

#### Analyze Document
```http
POST /api/v1/analyze/{document_id}
```

#### Check Status
```http
GET /api/v1/status/{document_id}
```

#### Analyze Single Clause
```http
POST /api/v1/analyze-clause
Content-Type: application/json

{
  "clause_text": "Your clause text here..."
}
```

#### Load RAG Dataset
```http
POST /api/v1/rag/load-dataset
```

### Response Structure

```json
{
  "document_id": "abc123...",
  "filename": "contract.pdf",
  "processed_at": "2024-01-15T10:30:00Z",
  "overall_risk_score": 45.5,
  "risk_summary": "MODERATE RISK CONTRACT with areas requiring attention.",
  "clauses": [
    {
      "text": "...",
      "type": "termination",
      "risk_level": "medium",
      "issue": "30-day notice may be insufficient",
      "suggestion": "Extend to 60 days",
      "negotiation": {
        "objective": "Extend termination notice period",
        "reason": "Operational continuity risk",
        "suggested_change": "Change to 60 days minimum",
        "leverage": "medium"
      }
    }
  ],
  "negotiation_summary": {
    "high_priority": [...],
    "medium_priority": [...],
    "low_priority": [...]
  },
  "improvements": [...],
  "final_summary": "..."
}
```

## System Components

### 1. PDF Processor
- Validates PDF files (MIME type, size, format)
- Detects text vs scanned PDFs
- Extracts text using pdfplumber or Tesseract OCR
- Normalizes and cleans extracted text
- Caches processed documents

### 2. Clause Segmenter
- Rule-based splitting (headings, numbering)
- NLP refinement using spaCy
- Handles various clause formats
- Extracts section numbers and headings

### 3. Gemini Engine
- Primary analysis engine using Gemini API
- Strict JSON output format
- Clause classification
- Risk detection
- Negotiation strategy generation
- Timeout and retry handling

### 4. Fallback Engine
- Activates when Gemini fails
- Rule-based classification using keywords
- Heuristic risk assessment
- Template-based negotiation strategies
- Ensures 100% analysis coverage

### 5. RAG Pipeline
- Supabase pgvector for vector storage
- Gemini embeddings for semantic search
- Retrieves similar clauses for context
- Enhances analysis accuracy

### 6. Risk Scorer
- Deterministic scoring algorithm
- Weights: High risk (+20), Missing clause (+15), Ambiguity (+10)
- Normalized to 0-100 scale
- Generates prioritized negotiation items

### 7. Validation Layer
- JSON schema validation
- Cross-checks with RAG data
- Normalizes outputs
- Ensures consistency

## Gemini Failure Handling

Fallback triggers when:
- API timeout > 5 seconds
- Invalid JSON response
- Empty response
- Rate limit hit

Retry strategy:
1. Retry up to 2 times with exponential backoff
2. Fall back to local engine if retries exhausted

## Performance Optimizations

- **Caching**: Parsed PDFs and embeddings are cached
- **Batch Processing**: Clauses processed in batches
- **Async Processing**: Non-blocking API calls
- **Connection Pooling**: Efficient database connections

## Security

- PDF MIME type validation
- File size limits (50MB default)
- Text sanitization before processing
- API keys stored in environment variables
- No sensitive data logged

## Project Structure

```
sentinel-legal/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py        # API endpoints
│   │   │   └── dependencies.py  # Dependency injection
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_processor.py
│   │   │   ├── clause_segmenter.py
│   │   │   ├── gemini_engine.py
│   │   │   ├── fallback_engine.py
│   │   │   ├── rag_pipeline.py
│   │   │   ├── risk_scorer.py
│   │   │   ├── validator.py
│   │   │   └── analysis_orchestrator.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py       # Pydantic models
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── data/
│   │   └── clause_dataset.json  # Training data
│   ├── .env
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── supabase_setup.sql
└── README.md
```

## Clause Types Supported

- Termination
- Liability
- Indemnification
- Confidentiality
- Intellectual Property
- Payment
- Warranty
- Force Majeure
- Dispute Resolution
- Governing Law
- Assignment
- Notice
- Amendment
- Severability
- Non-Compete
- Non-Solicitation
- Data Protection
- Compliance
- Insurance
- Audit Rights

## Risk Levels

| Level | Score Impact | Description |
|-------|-------------|-------------|
| High | +20 | Requires immediate attention and negotiation |
| Medium | +10 | Should be reviewed and potentially improved |
| Low | +0 | Standard clause with minimal risk |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GEMINI_API_KEY | Google Gemini API key | Required |
| SUPABASE_URL | Supabase project URL | Required |
| SUPABASE_ANON_KEY | Supabase anonymous key | Required |
| MAX_FILE_SIZE_MB | Maximum upload size | 50 |
| GEMINI_TIMEOUT | API timeout in seconds | 5 |
| TOP_K_RETRIEVAL | Number of similar clauses | 5 |

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
isort app/
```

### API Documentation
Visit `/docs` for interactive Swagger documentation.

## Troubleshooting

### Tesseract Not Found
Install Tesseract OCR:
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt install tesseract-ocr`
- Mac: `brew install tesseract`

### Poppler Not Found
Install Poppler for PDF processing:
- Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases
- Linux: `sudo apt install poppler-utils`
- Mac: `brew install poppler`

### spaCy Model Not Found
```bash
python -m spacy download en_core_web_sm
```

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open a GitHub issue.

---

**Sentinel Core** - AI-Powered Contract Intelligence
