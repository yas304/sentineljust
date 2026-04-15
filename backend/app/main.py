"""
Sentinel Core - AI Contract Intelligence Platform
Main FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import get_settings
from .api import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Sentinel Core...")
    settings = get_settings()
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sentinel Core...")


# Create FastAPI application
app = FastAPI(
    title="Sentinel Core",
    description="""
    AI-powered Contract Intelligence and Negotiation System.
    
    ## Features
    
    * **PDF Upload**: Process text and scanned PDFs
    * **Clause Analysis**: AI-powered clause classification and risk assessment
    * **Negotiation Strategies**: Actionable negotiation recommendations
    * **Risk Scoring**: Deterministic contract risk scoring
    * **RAG Pipeline**: Context-aware analysis using similar clauses
    
    ## Architecture
    
    * Gemini AI for primary analysis
    * Deterministic fallback engine
    * pgvector for semantic search
    * Production-grade validation layer
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount static files for frontend
# Path: backend/app/main.py -> go up to sentinel legal folder -> frontend
frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
print(f"Frontend path: {frontend_path}, exists: {frontend_path.exists()}")

if frontend_path.exists():
    # Mount static assets
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")
    
    # Serve index.html at root
    from fastapi.responses import FileResponse
    
    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))
    
    @app.get("/favicon.svg", include_in_schema=False)
    async def serve_favicon():
        return FileResponse(str(frontend_path / "favicon.svg"), media_type="image/svg+xml")
else:
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "Sentinel Core",
            "version": "1.0.0", 
            "status": "operational",
            "docs": "/docs",
            "note": "Frontend not found. API is operational."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
