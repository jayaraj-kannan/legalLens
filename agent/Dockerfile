# Google ADK Multi-Agent Server Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent definitions
COPY legallens/ ./legallens/

# Create directory for ADK local state/cache
RUN mkdir -p /app/.adk

# Non-root user
RUN adduser --disabled-password --gecos "" legallens && \
    chown -R legallens:legallens /app
USER legallens

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8000"]
