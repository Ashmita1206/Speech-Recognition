# ---------------------------------------------------------------------------
# Dockerfile — Speech Recognition Studio
# Production-ready Linux container image (Debian Bookworm, Python 3.12)
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    HF_HOME=/app/.hf_cache \
    WHISPER_MODEL=large-v3 \
    ENABLE_SYSTEM_COMMANDS=false \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (FFmpeg for multi-format audio conversion, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root application user (UID 1000)
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy dependency manifest first for optimal Docker layer caching
COPY requirements.txt .

# Upgrade pip/wheel and install pinned dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . .

# Create writable runtime directories and set ownership
RUN mkdir -p /app/static/uploads /app/static/spectrograms /app/.hf_cache && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose standard container port
EXPOSE 7860

# Health check to verify web server readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/ || exit 1

# Launch with Gunicorn:
# 1 worker with 4 threads is required to prevent duplicating in-memory Whisper weights
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 180 --access-logfile - --error-logfile - app:app"]
