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
    HTTPS_PROXY=${HTTPS_PROXY} \
    TZ=Asia/Shanghai

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

# Expose default port
EXPOSE 9000

# Run the application
CMD ["uv", "run", "python", "main.py"]
