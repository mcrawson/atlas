# ATLAS - Automated Thinking, Learning & Advisory System
# Multi-stage Dockerfile for production deployment

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Production
# ============================================================================
FROM python:3.12-slim as production

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash atlas

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=atlas:atlas atlas/ ./atlas/
COPY --chown=atlas:atlas config/ ./config/
COPY --chown=atlas:atlas data/ ./data/

# Create directories for runtime data
RUN mkdir -p /app/data /app/logs && \
    chown -R atlas:atlas /app

# Switch to non-root user
USER atlas

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ATLAS_ENV=production

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/api/health')" || exit 1

# Default command
CMD ["uvicorn", "atlas.web.app:app", "--host", "0.0.0.0", "--port", "8888"]

# ============================================================================
# Stage 3: Development
# ============================================================================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov ruff mypy

# Switch back to atlas user
USER atlas

# Override command for development
CMD ["uvicorn", "atlas.web.app:app", "--host", "0.0.0.0", "--port", "8888", "--reload"]
