# Deployment Guide

Last updated: 2026-05-09

## Overview

| Component | What it does |
|-----------|-------------|
| **Streamlit app** (`app.py`) | Web dashboard — serves the team |
| **Data collector** (`data_collection.py`) | Fetches daily OHLCV from yfinance / AkShare |
| **Cloud Scheduler** | Triggers the collector automatically every trading day |

**Current footprint:**
- 5 markets: Hong Kong, A-Share, Taiwan, South Korea, US
- 1 ETF per industry/theme per market (~50 ETFs total), grows ~5 KB/day
- No database — all state is flat CSVs stored in GCS

---

## Recommended: Google Cloud Run + Cloud Scheduler

**Why GCP:** No sleep/cold-start issues, native cron scheduler, scales to zero when idle, Hong Kong region for low latency, and IAP for team auth with zero code changes. Stays within the free tier for a small team.

### Architecture

```
Your machine (git push / gcp-deploy.sh)
    │
    ▼ Cloud Build (builds Docker image)
Artifact Registry
    │
    ├──▶ Cloud Run Service (rays-etf-app)   ←── team opens browser
    │         │ gcsfuse mounts /data
    │         ▼
    │    GCS bucket (gs://rays-capital-etf-data/)
    │         ▲
    └──▶ Cloud Run Job (rays-collector)
              │ triggered by Cloud Scheduler
              └── daily 08:00 HKT (Tue–Sat) → python data_collection.py → CSVs → GCS
```

### GCP services used

| Role | Service | Free tier |
|------|---------|-----------|
| Web dashboard | Cloud Run (gen2) | 2M requests/month, 360K GB-sec compute |
| Daily data collection | Cloud Run Job | Included in Cloud Run free tier |
| Cron trigger | Cloud Scheduler | 3 jobs free |
| CSV storage | Cloud Storage (GCS) | 5 GB free (asia regions) |
| Docker images | Artifact Registry | 0.5 GB free |

**Cost: $0/month** for a small team dashboard. Billable only if exceeding 2M requests/month — very unlikely.

---

## Step-by-Step: First-Time Deploy

### Prerequisites

- A Google account
- `gcloud` CLI installed — [install guide](https://cloud.google.com/sdk/docs/install)
- The project code on your local machine

---

### Step 1 — Create a GCP project and attach billing

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown → **New Project**
3. Name it (e.g. `rays-capital-stock-dashboard`) and note the **Project ID**
4. Go to **Billing** in the left menu → link a billing account

> Billing is required to unlock Cloud Run even on the free tier. You will not be charged as long as usage stays within free limits.

---

### Step 2 — Authenticate the gcloud CLI

```bash
gcloud auth login
gcloud auth application-default login
```

---

### Step 3 — Edit the deploy script config

Open [gcp-deploy.sh](../gcp-deploy.sh) and set these four variables at the top:

```bash
PROJECT_ID="rays-capital-stock-dashboard"   # your GCP project ID
REGION="asia-east1"                         # Hong Kong — keep this
BUCKET_NAME="rays-capital-etf-data"        # must be globally unique
APP_NAME="rays-etf-app"
```

---

### Step 4 — Run the deploy script

```bash
chmod +x gcp-deploy.sh
./gcp-deploy.sh
```

The script does everything in one run:

| Step | What happens |
|------|-------------|
| 1 | Sets the active GCP project |
| 2 | Enables required APIs (Cloud Run, Cloud Build, Scheduler, GCS, IAM) |
| 3 | Creates the GCS bucket for CSV storage |
| 4 | Creates the Artifact Registry Docker repository |
| 5 | Builds and pushes the Docker image via Cloud Build (no local Docker needed) |
| 6 | Creates a service account with GCS read/write permissions |
| 7 | Deploys the Streamlit app to Cloud Run |
| 8 | Deploys the data collector as a Cloud Run Job |
| 9 | Runs the collector immediately to seed all data (~20–40 min first run) |
| 10 | Creates the Cloud Scheduler job (daily 08:00 HKT, Tue–Sat) |

At the end it prints the **App URL** — share that with the team.

---

### Step 5 — Verify

1. Open the App URL in a browser — the dashboard should load
2. Check GCS bucket has data: `gsutil ls gs://rays-capital-etf-data/`
3. Check the collector job ran: **Cloud Console → Cloud Run → Jobs → rays-collector → Executions**

---

## Updating After Code Changes

When you push code changes (new ETFs, new pages, bug fixes), redeploy with one command:

```bash
./gcp-deploy.sh update
```

This rebuilds the Docker image and redeploys the app. The Cloud Run Job picks up the new image automatically on its next scheduled run, or update it manually:

```bash
gcloud run jobs update rays-collector \
  --image asia-east1-docker.pkg.dev/rays-capital-stock-dashboard/rays/rays-etf-app:latest \
  --region asia-east1
```

---

## Resetting Data (e.g. after config changes)

If ETF configs change significantly (markets added/removed, ETFs swapped), wipe the old CSVs and re-collect:

```bash
# 1. Delete all existing CSV data from GCS (quotes prevent zsh glob expansion)
gsutil -m rm "gs://rays-capital-etf-data/**"

# 2. Redeploy the app with the new code
./gcp-deploy.sh update

# 3. Update the collector job image
gcloud run jobs update rays-collector \
  --image asia-east1-docker.pkg.dev/rays-capital-stock-dashboard/rays/rays-etf-app:latest \
  --region asia-east1

# 4. Trigger a full re-collection (~20–40 min)
gcloud run jobs execute rays-collector --region asia-east1 --wait
```

---

## Adding Team Access (IAP Auth)

By default the app is public (`--allow-unauthenticated`). To restrict to specific Google accounts:

```bash
# Remove public access
gcloud run services remove-iam-policy-binding rays-etf-app \
  --region asia-east1 \
  --member="allUsers" \
  --role="roles/run.invoker"

# Grant access to each team member (repeat per person)
gcloud run services add-iam-policy-binding rays-etf-app \
  --region asia-east1 \
  --member="user:teammate@gmail.com" \
  --role="roles/run.invoker"
```

Team members will be prompted to sign in with their Google account when visiting the URL.

---

## Pre-deployment Checklist

- [x] `utils/config.py` reads `DATA_ROOT` from env var (defaults to `.` locally)
- [x] `utils/data.py` resolves all CSV paths via `_data()` helper
- [x] `data_collection.py` resolves paths via `_data()` and `_app()`
- [x] `Dockerfile` installs gcsfuse, uses gen2, exposes port 8080
- [x] `docker-entrypoint.sh` mounts GCS bucket at `/data` then starts Streamlit
- [x] `gcp-deploy.sh` scripted end-to-end (all 10 steps)
- [x] `data/`, `data_ashare/`, `data_tw/`, `data_sk/`, `data_us/` are in `.gitignore`
- [x] No hardcoded secrets or local absolute paths in app code
- [ ] GCP project created and billing account attached
- [ ] `PROJECT_ID` and `BUCKET_NAME` set in `gcp-deploy.sh`
- [ ] `./gcp-deploy.sh` run successfully — App URL confirmed working
- [ ] (Optional) IAP bindings added for team members

---

## Alternative: Render (Backup Option)

Render is simpler to set up but has notable limitations for this use case:

| | Render (free) | GCP Cloud Run |
|--|---------------|---------------|
| Cold start | ~30 sec (sleeps after 15 min idle) | ~3–5 sec (scales to zero, not sleep) |
| Storage | 1 GB disk, single-mount | 5 GB GCS, shared across jobs |
| Auth | Manual (`st.secrets`) or paid plan | IAP — Google account gating, free |
| Scheduler | 1-hr minimum interval | Any cron schedule |
| Region | US only | asia-east1 (Hong Kong) |
| Setup | Connect GitHub repo, done | Run `./gcp-deploy.sh` once |

Only consider Render if the team has no Google accounts or no ability to attach a billing account to GCP.
