"""
Vercel Serverless Function Entry Point
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment defaults for Vercel
os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")
os.environ.setdefault("CACHE_DIR", "/tmp/cache")

# Import the FastAPI app
from app.main import app

# Export for Vercel
handler = app
