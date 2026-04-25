# Drama Web Crawler - Test Environment Dockerfile
# Based on Python 3.12 slim image

FROM python:3.12-slim

# Build args for proxy (pass at build time)
ARG HTTP_PROXY
ARG HTTPS_PROXY

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY}

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY main.py ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
RUN mkdir -p /app/logs /app/data && chown -R appuser:appuser /app/logs /app/data
USER appuser

# Expose default port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9000/api/v1/healthz', timeout=5).raise_for_status()" || exit 1

# Run the application
CMD ["uv", "run", "python", "main.py"]
