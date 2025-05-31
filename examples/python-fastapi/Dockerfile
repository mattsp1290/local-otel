# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 canary && \
    mkdir -p /app && \
    chown -R canary:canary /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/canary/.local

# Copy application code
COPY --chown=canary:canary . .

# Switch to non-root user
USER canary

# Add local bin to PATH
ENV PATH=/home/canary/.local/bin:$PATH

# Environment variables with defaults
ENV SERVICE_NAME=canary-api \
    SERVICE_VERSION=1.0.0 \
    OTLP_ENDPOINT=http://telemetry-nest-otel-collector:4318/v1/traces \
    STATSD_HOST=telemetry-nest-statsd \
    STATSD_PORT=8125 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/chirp || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
