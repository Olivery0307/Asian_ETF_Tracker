#!/bin/bash
set -e

# Mount GCS bucket at /data so all CSV reads/writes resolve correctly.
# Requires Cloud Run gen2 execution environment (allows FUSE mounts).
# GCS_BUCKET env var must be set (e.g. "rays-etf-data").
if [ -n "$GCS_BUCKET" ]; then
    echo "Mounting gs://$GCS_BUCKET at /data..."
    gcsfuse --implicit-dirs "$GCS_BUCKET" /data
    echo "GCS mount OK"
else
    echo "GCS_BUCKET not set — using local /data (dev mode)"
fi

# Cloud Run sets $PORT dynamically; default to 8080
PORT="${PORT:-8080}"

exec streamlit run app.py \
    --server.port="$PORT" \
    --server.address=0.0.0.0 \
    --server.headless=true
