# Multi-stage Dockerfile for SecureRAG FastAPI Backend

FROM python:3.11-slim as base

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for psycopg / build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Expose backend port
EXPOSE 8000

# Run Uvicorn server in production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
