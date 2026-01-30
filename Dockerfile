# =============================================================================
# DOCKERFILE FOR DJANGO BACKEND
# Production-ready with Gunicorn
# Supports: Render, Railway, Docker Compose, VPS
# =============================================================================
FROM python:3.11-slim

# Build arguments
ARG ENVIRONMENT=production

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PORT=8000
ENV DJANGO_SETTINGS_MODULE=marsdevs.settings

# Working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    stockfish \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p /app/media /app/staticfiles

# Collect static files (with dummy secret key for build)
RUN SECRET_KEY=build-key python manage.py collectstatic --noinput --clear 2>/dev/null || true

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/ || exit 1

# Start command
CMD ["/app/start.sh"]
