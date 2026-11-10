# =========================================================
# Stage 1: Build Frontend Single Page Application
# =========================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json ./
RUN npm install --ignore-scripts

# Build production distribution
COPY frontend/ ./
RUN npm run build

# =========================================================
# Stage 2: Production Python Runtime Environment
# =========================================================
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    ENABLE_EXTERNAL_SERVICES=false

WORKDIR /app

# Install runtime utilities for container health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and configurations
COPY main.py ./
COPY app/ ./app/
COPY conf/ ./conf/

# Copy compiled static frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose server port
EXPOSE 8000

# Automated container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn ASGI server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

