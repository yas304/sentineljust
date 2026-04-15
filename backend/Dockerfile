FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libmagic1 \
    tesseract-ocr \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements-railway.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-railway.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY app/ ./app/

# Copy startup script and fix line endings
COPY start.sh .
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Create necessary directories
RUN mkdir -p /app/uploads /app/cache /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["./start.sh"]
