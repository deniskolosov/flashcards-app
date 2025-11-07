# Multi-stage Dockerfile for Flashcard Study App
# Supports both development and production builds

# ================================
# Base Stage - Common Dependencies
# ================================
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Install uv for fast Python package management
RUN pip install uv

# ================================
# Dependencies Stage
# ================================
FROM base AS deps

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install Python dependencies
RUN uv sync --frozen

# ================================
# Development Stage
# ================================
FROM deps AS development

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Switch to app user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Development command (will be overridden by docker-compose)
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ================================
# Production Build Stage
# ================================
FROM deps AS builder

# Copy application code
COPY . .

# Build any assets or perform optimizations here
# (Currently not needed for this FastAPI app, but structure is ready)

# ================================
# Production Runtime Stage
# ================================
FROM python:3.13-slim AS production

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependencies from deps stage
COPY --from=deps /root/.local /root/.local
COPY --from=deps /app/.venv /app/.venv

# Copy application code from builder
COPY --from=builder --chown=appuser:appuser /app/backend ./backend
COPY --from=builder --chown=appuser:appuser /app/frontend ./frontend
COPY --from=builder --chown=appuser:appuser /app/alembic ./alembic
COPY --from=builder --chown=appuser:appuser /app/alembic.ini ./
COPY --from=builder --chown=appuser:appuser /app/pyproject.toml ./

# Create necessary directories
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Switch to app user for security
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ================================
# Testing Stage (for CI/CD)
# ================================
FROM development AS testing

# Install additional test dependencies if needed
# (Already included in dev dependencies)

# Copy test files
COPY --chown=appuser:appuser tests/ ./tests/

# Run tests as part of build (optional - can be run separately in CI)
# RUN uv run pytest tests/ -v

# Command for running tests
CMD ["uv", "run", "pytest", "tests/", "-v", "--tb=short"]