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

## Option B — Google Cloud Run + Cloud Scheduler ✅ (Active)

**Best for:** No sleep/cold-start issues, native cron, scales to zero when idle.

### Components

| Role | GCP service | Free tier |
|------|------------|-----------|
| Streamlit app | **Cloud Run** (gen2) | 2M requests/month, 360K GB-sec compute |
| Daily scheduler | **Cloud Scheduler** | 3 jobs free |
| CSV storage | **Cloud Storage** (GCS) | 5 GB free (US regions) |
| Docker images | **Artifact Registry** | 0.5 GB free |

### Architecture

```
GitHub repo (no data/ dirs)
    │
    ▼ docker build + push
Artifact Registry  ──▶  Cloud Run app (gen2)
                              │ gcsfuse mounts /data
                         GCS bucket gs://rays-etf-data/
                              ▲
Cloud Scheduler (daily 08:00 HKT)
    │
    ▼
Cloud Run Job (rays-collector)
    gcsfuse mounts /data → python data_collection.py → writes CSVs → GCS
```

**Key design:** GCS bucket is FUSE-mounted at `/data` inside the container via `gcsfuse`.
No Python code changes needed — all existing `_data(path)` calls resolve normally.
Requires Cloud Run **gen2** execution environment to allow FUSE mounts.

### Deploy

Everything is scripted. Edit the config block at the top of [gcp-deploy.sh](../gcp-deploy.sh)
then run it once:

```bash
# 1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
# 2. Authenticate
gcloud auth login
gcloud auth application-default login

# 3. Create a GCP project at console.cloud.google.com and attach a billing account
#    (required to unlock Cloud Run — stays within free tier)

# 4. Edit PROJECT_ID and BUCKET_NAME in gcp-deploy.sh, then:
chmod +x gcp-deploy.sh
./gcp-deploy.sh
```

The script does all 9 steps: enable APIs → create bucket → build image → deploy app
→ deploy collector job → seed data → create daily scheduler.

### Updating after code changes

```bash
PROJECT_ID="rays-etf"
REGION="asia-east1"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/rays/rays-etf-app"

docker build -t $IMAGE:latest . && docker push $IMAGE:latest
gcloud run deploy rays-etf-app --image $IMAGE:latest --region $REGION
```

### Adding team auth (IAP)

To restrict the app to specific Google accounts (no code changes):
```bash
# Remove public access
gcloud run services remove-iam-policy-binding rays-etf-app \
  --region asia-east1 --member="allUsers" --role="roles/run.invoker"

# Grant access to a teammate
gcloud run services add-iam-policy-binding rays-etf-app \
  --region asia-east1 \
  --member="user:teammate@company.com" \
  --role="roles/run.invoker"
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

- [x] `requirements.txt` is complete and pinned
- [x] `data/`, `data_ashare/`, `data_tw/`, `data_sk/` are in `.gitignore`
- [x] `archive/`, `reports/` are in `.gitignore`
- [x] `utils/config.py` reads data root from env var `DATA_ROOT` (defaults to `.` locally)
- [x] `utils/data.py` resolves all CSV paths via `_data()` helper
- [x] `data_collection.py` resolves data dirs via `_data()`, config files via `_app()`
- [x] `scheduler.py` uses UTC (`datetime.now(timezone.utc)`), log written to `DATA_ROOT`
- [x] `Dockerfile` updated for GCS FUSE (gcsfuse installed, gen2, port 8080)
- [x] `docker-entrypoint.sh` mounts GCS bucket at `/data` then starts Streamlit
- [x] `gcp-deploy.sh` scripted end-to-end: bucket → image → app → job → scheduler
- [x] `gcsfs` added to `requirements.txt` as local dev fallback
- [x] No hardcoded secrets or local absolute paths in app code
- [ ] Create GCP project at console.cloud.google.com and attach billing account
- [ ] Set `PROJECT_ID` and `BUCKET_NAME` in `gcp-deploy.sh` then run it
- [ ] Data seeded automatically by script (Step 8 runs collector on first deploy)
- [ ] (Optional) Remove `--allow-unauthenticated` and add per-user IAP bindings for team auth
