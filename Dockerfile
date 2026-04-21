FROM python:3.12-slim

# ── System dependencies ───────────────────────────────────────────────────────
# gcsfuse: mounts a GCS bucket as a local filesystem at /data (requires gen2)
# Uses modern apt signed-by approach (apt-key is deprecated in Debian bookworm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    curl \
    gnupg \
    fuse \
    ca-certificates \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
       | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt gcsfuse-bookworm main" \
       > /etc/apt/sources.list.d/gcsfuse.list \
    && apt-get update && apt-get install -y --no-install-recommends gcsfuse \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
# Data lives in GCS, not in the image
COPY app.py .
COPY data_collection.py .
COPY scheduler.py .
COPY run_daily_update.py .
COPY utils/ ./utils/
COPY _pages/ ./_pages/
COPY *.json ./

# ── Runtime config ────────────────────────────────────────────────────────────
# DATA_ROOT: gcsfuse mounts the GCS bucket here at container start
# GCS_BUCKET: set via --set-env-vars at deploy time (e.g. "rays-etf-data")
ENV DATA_ROOT=/data
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true

# /data mount point for gcsfuse
RUN mkdir -p /data

EXPOSE 8080

# ── Entrypoint ────────────────────────────────────────────────────────────────
# 1. Mount GCS bucket at /data via gcsfuse
# 2. Start Streamlit on Cloud Run's dynamic $PORT (defaults to 8080)
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh
CMD ["./docker-entrypoint.sh"]
