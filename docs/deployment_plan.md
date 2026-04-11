# Deployment Plan

Last updated: 2026-04-10

## Overview

| Component | What it does |
|-----------|-------------|
| **Streamlit app** (`app.py`) | Web dashboard — serves the team |
| **Data collector** (`data_collection.py`) | Fetches daily OHLCV from yfinance / AkShare |
| **Scheduler** (`scheduler.py`) | Triggers data collection on a daily cron |

**Current footprint:**
- ~6 MB of CSV price data (4 markets, 309 ETFs, grows ~50 KB/day)
- Python dependencies: streamlit, plotly, yfinance, akshare, pandas, numpy
- No database — all state is flat CSVs on disk

---

## Option A — Render (Recommended free tier)

**Best for:** Quickest path to a shareable URL with zero DevOps overhead.

### Components

| Role | Render service | Free tier limit |
|------|---------------|-----------------|
| Streamlit app | **Web Service** (Docker or Python) | 750 hrs/month, sleeps after 15 min idle |
| Daily data collection | **Cron Job** | 1 job free, minimum 1-hour interval |
| CSV data persistence | **Persistent Disk** | 1 GB free (attached to the cron job service) |

### Architecture

```
GitHub repo (no data/ dirs — gitignored)
       │
       ▼
Render Web Service  ──── reads CSVs ────▶  Persistent Disk (1 GB)
                                                   ▲
Render Cron Job  ── runs daily at 8am HKT ─────────┘
(python data_collection.py)
```

### Steps

1. **Persistent disk** — create a 1 GB disk in Render, mount at `/data` on both services
2. **Environment** — set `DATA_ROOT=/data` env var; update `utils/config.py` to read it:
   ```python
   import os
   DATA_ROOT = os.getenv("DATA_ROOT", ".")  # local default = project dir
   ```
3. **Web Service** — connect GitHub repo, set start command:
   ```bash
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
4. **Cron Job** — set schedule `0 8 * * 2-6` (Tue–Sat 08:00 UTC+8 = Mon–Fri close+1):
   ```bash
   python data_collection.py
   ```
5. **Auth** — Render does not provide built-in auth on free tier; add Streamlit's built-in
   password via `st.secrets` or restrict by IP using Render's team settings (paid)

### Limitations
- Web service sleeps after 15 min of inactivity — first load takes ~30 sec to wake
- Cron job and web service share a disk but run as separate containers; disk must be
  mounted read-write on both (Render supports this on paid plans — see below)
- Free cron minimum interval: 1 hour (daily is fine)

### Cost: **$0/month**

---

## Option B — Google Cloud Run + Cloud Scheduler

**Best for:** No sleep/cold-start issues, native cron, scales to zero when idle.

### Components

| Role | GCP service | Free tier |
|------|------------|-----------|
| Streamlit app | **Cloud Run** | 2M requests/month, 360K GB-sec compute |
| Daily scheduler | **Cloud Scheduler** | 3 jobs free |
| CSV storage | **Cloud Storage** (GCS) bucket | 5 GB free (US regions) |

### Architecture

```
GitHub repo
    │
    ▼ (Cloud Build trigger on push)
Docker image  ──▶  Artifact Registry  ──▶  Cloud Run (app)
                                                  │ reads/writes
Cloud Scheduler  ──▶  Cloud Run (collector job)  ─┘
                       (or Cloud Run Jobs)         ▼
                                             GCS bucket
                                             gs://rays-etf-data/
```

### Steps

1. **GCS bucket** — `gsutil mb gs://rays-etf-data` in `asia-east1` (Hong Kong region)
2. **Adapt data paths** — replace local CSV reads with `gcsfs` or mount via Cloud Storage FUSE:
   ```python
   # utils/config.py
   import os
   DATA_BUCKET = os.getenv("GCS_BUCKET", "")  # e.g. "rays-etf-data"
   ```
   Or simpler: mount GCS as a FUSE volume in the Cloud Run container (requires `--execution-environment gen2`)
3. **Dockerfile**
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
4. **Deploy app**
   ```bash
   gcloud run deploy rays-etf-app \
     --source . --region asia-east1 \
     --allow-unauthenticated \
     --set-env-vars GCS_BUCKET=rays-etf-data
   ```
5. **Deploy collector as Cloud Run Job**
   ```bash
   gcloud run jobs create rays-collector \
     --image gcr.io/PROJECT/rays-etf-app \
     --command "python data_collection.py" \
     --region asia-east1
   ```
6. **Cloud Scheduler** — trigger collector job daily:
   ```bash
   gcloud scheduler jobs create http rays-daily \
     --schedule "0 8 * * 2-6" \
     --time-zone "Asia/Hong_Kong" \
     --uri "https://REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT/jobs/rays-collector:run" \
     --oauth-service-account-email SA@PROJECT.iam.gserviceaccount.com
   ```
7. **Auth** — use Cloud Run's built-in IAP (Identity-Aware Proxy) to restrict to team
   Google accounts — no code changes needed, toggle in Console

### Limitations
- Requires a GCP project (free, but needs billing account attached to unlock Cloud Run)
- GCS FUSE adds latency on first read; alternatively, use `gcsfs` library and rewrite
  all `pd.read_csv(path)` calls to `pd.read_csv(f"gcs://rays-etf-data/{path}")`
- Cold start on Cloud Run: ~3–5 sec (much better than Render's 30 sec)

### Cost: **$0/month** (within free tier for a small team)
Billable only if exceeding 2M requests/month or 360K GB-seconds compute — unlikely
for a team dashboard with daily traffic.

---

## Comparison

| | Render | Google Cloud Run |
|--|--------|-----------------|
| Setup difficulty | Low — connect GitHub, done | Medium — Docker, GCS, IAM |
| Cold start | ~30 sec (sleeps on idle) | ~3–5 sec (scales to zero, not sleep) |
| Persistent storage | 1 GB disk (free, single-mount) | 5 GB GCS (free, shared) |
| Auth | Manual (st.secrets) or paid | IAP — Google account gating |
| Cron | 1 free job, 1-hr minimum | 3 free jobs, any schedule |
| Region | US-based (latency to HK) | asia-east1 (Hong Kong) — lower latency |
| **Verdict** | Best for getting started today | Best if team uses Google Workspace |

**Recommendation:** Start with **Render** (zero config). Migrate to **GCP** when the team
grows or you need IAP auth and lower latency.

---

## Paid Options (When Scale Demands It)

### Trigger points to consider upgrading
- Team > 10 concurrent users
- Data > 10 GB (multiple years, more markets)
- Need for guaranteed uptime SLA
- Want built-in SSO / audit logging

### Paid options

| Option | Best for | Est. monthly cost |
|--------|----------|-------------------|
| **Render Starter** | No-sleep web service + shared disk | ~$21/mo (web $7 + disk $0.25/GB) |
| **Streamlit Community Cloud** (free) | Streamlit-only, no scheduler | $0 — but no persistent disk or cron |
| **Streamlit for Teams** | Managed auth, secrets, sharing | ~$250/mo (teams plan) |
| **GCP Cloud Run + Cloud SQL** | Replace CSVs with Postgres, auto-scale | ~$30–80/mo depending on load |
| **AWS App Runner + S3 + EventBridge** | Full AWS stack, same pattern as GCP | ~$25–60/mo |
| **Azure Container Apps + Blob Storage** | Teams using Microsoft 365 / AAD | ~$20–50/mo |
| **Heroku Eco Dyno** | Simple Heroku deployment | ~$5/mo (but no persistent disk) |

### Recommended upgrade path

```
Free Render  →  Render Starter ($21/mo)  →  GCP Run + Cloud SQL (~$50/mo)
                (remove sleep, real disk)     (proper DB, autoscale, IAP auth)
```

At the GCP tier, replace flat CSVs with a **PostgreSQL** table
`(market, theme, code, date, open, high, low, close, volume)` — eliminates
file-system persistence complexity and makes the scheduler stateless.

---

## Pre-deployment Checklist

- [ ] `requirements.txt` is complete and pinned (`pip freeze > requirements.txt`)
- [ ] `data/`, `data_ashare/`, `data_tw/`, `data_sk/` are in `.gitignore` (already done)
- [ ] `archive/` is in `.gitignore` (already done)
- [ ] `utils/config.py` reads data root from env var `DATA_ROOT`
- [ ] `scheduler.py` uses UTC times, not local machine time
- [ ] App tested with `streamlit run app.py --server.headless true`
- [ ] Secrets (API keys, if any added later) stored in env vars, not hardcoded
