FROM python:3.11-slim

# Install ffmpeg for fast thumbnail extraction
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Environment defaults
ENV RECORDINGS_PATH=/recordings \
    RETENTION_DAYS=30 \
    CLEANUP_INTERVAL_HOURS=6 \
    CACHE_PATH=/tmp/reoftpview_cache \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
