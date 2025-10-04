# Multi-stage Dockerfile for SRE Bot Strands
# Uses Python 3.11 slim and uv for fast dependency management

FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .python-version uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy uv binary for MCP server execution (needed by FinOps agent)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create uvx symlink for MCP server execution
RUN ln -s /usr/local/bin/uv /usr/local/bin/uvx

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/sessions && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

# Switch to non-root user
USER appuser

# Expose port (can be overridden by docker-compose)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Default command (will be overridden by docker-compose for different services)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
