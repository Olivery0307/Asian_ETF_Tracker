FROM python:3.12-slim

# System deps for akshare / lxml / curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (not data — data lives on persistent disk)
COPY app.py .
COPY data_collection.py .
COPY scheduler.py .
COPY run_daily_update.py .
COPY utils/ ./utils/
COPY _pages/ ./_pages/
COPY *.json ./

# DATA_ROOT is set at runtime by Render to the persistent disk mount point.
# Locally it defaults to "." so existing workflows are unchanged.
ENV DATA_ROOT=/data

# Streamlit config — disable telemetry, set port
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
