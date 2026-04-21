#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# GCP Deployment Script — ETF Dashboard
#
# Deploys:
#   1. GCS bucket           — persistent CSV storage
#   2. Artifact Registry    — Docker image repository
#   3. Cloud Run app        — Streamlit web dashboard
#   4. Cloud Run Job        — data collection job
#   5. Cloud Scheduler      — daily trigger for the collector job
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - Docker running locally
#   - Billing account attached to the GCP project
#
# Usage:
#   chmod +x gcp-deploy.sh
#   ./gcp-deploy.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── CONFIGURATION — edit these before running ─────────────────────────────────
PROJECT_ID="rays-capital-stock-dashboard"
REGION="asia-east1"
BUCKET_NAME="rays-capital-etf-data"
APP_NAME="rays-etf-app"
JOB_NAME="rays-collector"
SCHEDULER_NAME="rays-daily"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/rays/$APP_NAME"
# ─────────────────────────────────────────────────────────────────────────────

# ── Quick update mode: just rebuild image + redeploy app ──────────────────────
# Usage: ./gcp-deploy.sh update
if [ "${1:-}" = "update" ]; then
    echo "=== Quick update: build + deploy app only ==="
    gcloud config set project "$PROJECT_ID"
    gcloud builds submit --tag "$IMAGE:latest" --project "$PROJECT_ID" .
    gcloud run deploy "$APP_NAME" --image "$IMAGE:latest" --region "$REGION"
    APP_URL=$(gcloud run services describe "$APP_NAME" --region "$REGION" --format "value(status.url)")
    echo "Done. App URL: $APP_URL"
    exit 0
fi
# ─────────────────────────────────────────────────────────────────────────────

echo "=== Step 0: Set project ==="
gcloud config set project "$PROJECT_ID"

echo ""
echo "=== Step 1: Enable required APIs ==="
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    iam.googleapis.com

echo ""
echo "=== Step 2: Create GCS bucket (CSV storage) ==="
# asia-east1 = Hong Kong. Standard storage class.
gsutil mb -l "$REGION" -c STANDARD "gs://$BUCKET_NAME" 2>/dev/null \
    || echo "Bucket already exists, skipping."

echo ""
echo "=== Step 3: Create Artifact Registry repository ==="
gcloud artifacts repositories create rays \
    --repository-format=docker \
    --location="$REGION" \
    --description="ETF dashboard images" 2>/dev/null \
    || echo "Repository already exists, skipping."

# Enable Cloud Build API (needed for gcloud builds submit)
gcloud services enable cloudbuild.googleapis.com --project "$PROJECT_ID"

echo ""
echo "=== Step 4: Build and push Docker image (via Cloud Build — no local Docker needed) ==="
gcloud builds submit \
    --tag "$IMAGE:latest" \
    --project "$PROJECT_ID" \
    .

echo ""
echo "=== Step 5: Create Service Account for Cloud Run ==="
SA_NAME="rays-runner"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

gcloud iam service-accounts create "$SA_NAME" \
    --display-name="ETF Dashboard Runner" 2>/dev/null \
    || echo "Service account already exists, skipping."

# Grant GCS read/write access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin" \
    --condition=None

# Grant Cloud Run invoker (needed by Cloud Scheduler)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker" \
    --condition=None

echo ""
echo "=== Step 6: Deploy Streamlit app to Cloud Run ==="
gcloud run deploy "$APP_NAME" \
    --image "$IMAGE:latest" \
    --region "$REGION" \
    --platform managed \
    --execution-environment gen2 \
    --allow-unauthenticated \
    --service-account "$SA_EMAIL" \
    --set-env-vars "GCS_BUCKET=$BUCKET_NAME,DATA_ROOT=/data" \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --port 8080

echo ""
echo "=== Step 7: Deploy data collector as Cloud Run Job ==="
gcloud run jobs create "$JOB_NAME" \
    --image "$IMAGE:latest" \
    --region "$REGION" \
    --execution-environment gen2 \
    --service-account "$SA_EMAIL" \
    --set-env-vars "GCS_BUCKET=$BUCKET_NAME,DATA_ROOT=/data" \
    --memory 1Gi \
    --cpu 1 \
    --command "/bin/bash" \
    --args "-c,gcsfuse --implicit-dirs $BUCKET_NAME /data && python data_collection.py" \
    --max-retries 2 \
    --task-timeout 3600 2>/dev/null \
    || gcloud run jobs update "$JOB_NAME" \
        --image "$IMAGE:latest" \
        --region "$REGION" \
        --set-env-vars "GCS_BUCKET=$BUCKET_NAME,DATA_ROOT=/data"

echo ""
echo "=== Step 8: Seed data on first deploy ==="
echo "Running collector now to populate GCS bucket..."
gcloud run jobs execute "$JOB_NAME" --region "$REGION" --wait

echo ""
echo "=== Step 9: Create Cloud Scheduler — daily at 08:00 HKT (00:00 UTC) Tue-Sat ==="
JOB_URI="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run"

gcloud scheduler jobs create http "$SCHEDULER_NAME" \
    --location "$REGION" \
    --schedule "0 0 * * 2-6" \
    --time-zone "Asia/Hong_Kong" \
    --uri "$JOB_URI" \
    --http-method POST \
    --oauth-service-account-email "$SA_EMAIL" \
    --attempt-deadline 30m 2>/dev/null \
    || echo "Scheduler job already exists, skipping."

echo ""
echo "=== Done ==="
APP_URL=$(gcloud run services describe "$APP_NAME" --region "$REGION" --format "value(status.url)")
echo "App URL: $APP_URL"
echo "Bucket:  gs://$BUCKET_NAME"
echo ""
echo "Next steps:"
echo "  - Open $APP_URL in your browser"
echo "  - To add auth: gcloud run services add-iam-policy-binding $APP_NAME --region $REGION --member='user:EMAIL' --role='roles/run.invoker'"
echo "  - To update after code changes: gcloud builds submit --tag $IMAGE:latest . && gcloud run deploy $APP_NAME --image $IMAGE:latest --region $REGION"
