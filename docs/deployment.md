# Deployment Guide

This guide covers the deployment architecture, CI/CD workflow, and configuration for the PSX Research Agent application.

## Overview

The application is deployed to **Google Cloud Run** using a **GitHub Actions** CI/CD pipeline. The deployment process automatically builds a Docker image, pushes it to Artifact Registry, and deploys it to Cloud Run whenever code is pushed to the `main` branch.

## Architecture

```
GitHub Repository (main branch)
    ↓
GitHub Actions Workflow
    ↓
Build Docker Image
    ↓
Push to Artifact Registry
    ↓
Deploy to Cloud Run
```

## CI/CD Workflow

The CI/CD workflow is defined in `.github/workflows/deploy.yml` and runs automatically on:

- **Push to main branch** - Automatic deployment
- **Manual trigger** - Via GitHub Actions UI (workflow_dispatch)

### Workflow Steps

1. **Checkout code** - Retrieves the latest code from the repository
2. **Authenticate to Google Cloud** - Uses Workload Identity Federation (WIF) for secure authentication
3. **Set up Cloud SDK** - Configures gcloud CLI
4. **Configure Docker** - Sets up Docker authentication for Artifact Registry
5. **Build Docker image** - Creates image tagged with both `GITHUB_SHA` and `latest`
6. **Push Docker image** - Uploads image to Artifact Registry
7. **Deploy to Cloud Run** - Deploys the new image to Cloud Run service
8. **Clean up old images** - Removes old images to stay within free tier limits

### Authentication

The workflow uses **Workload Identity Federation** (WIF) instead of service account keys for enhanced security. See [GitHub Secrets Setup Guide](github-secrets-setup.md) for initial configuration.

## Health Checks

### Health Check Endpoint

The application exposes a health check endpoint at `/health`:

```bash
GET /health
```

**Response**:
```json
{
  "status": "healthy"
}
```

This endpoint is used by Cloud Run to verify the application is running correctly.

### Startup Probe Configuration

Cloud Run is configured with a startup probe to handle cold starts gracefully:

```yaml
startup-probe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  timeoutSeconds: 10
  periodSeconds: 10
  failureThreshold: 30
```

**Configuration Details**:
- **Initial Delay**: 10 seconds before first probe
- **Timeout**: 10 seconds per probe attempt
- **Period**: 10 seconds between probes
- **Failure Threshold**: 30 failures allowed (5 minutes total)

This allows up to 5 minutes for the application to start, which is important for cold starts when dependencies need to be downloaded and initialized.

## Image Management

### Cleanup Strategy

The CI/CD workflow includes automatic image cleanup to stay within Google Cloud's free tier limits (500MB storage).

**Cleanup Logic**:
- Keeps only the **1 newest image** (by creation time)
- Deletes all older images after successful deployment
- Runs only if deployment succeeds (`if: success()`)
- Uses SHA256 digest to identify unique images
- Deletes images by digest to ensure complete removal
- Uses CSV format for reliable parsing of image references
- **Retry logic**: Retries failed deletions up to 2 times with 2-second delays
- **Verification**: Verifies the kept image still exists after cleanup
- **Error tracking**: Reports success/failure counts for transparency

**Reliability Features**:
- ✅ Retry mechanism for transient failures
- ✅ Verification step to ensure kept image exists
- ✅ Detailed logging of deletion attempts
- ✅ Error handling that continues even if some deletions fail

**Important**: The cleanup runs AFTER deployment, so the newly pushed image is included in the list. The script keeps the first (newest) image and deletes all others. 

**Note on Orphaned Layers**: While the cleanup script is robust, orphaned layers can still occur in rare cases:
- Network failures during deletion
- Concurrent operations
- Shared layers between images (minimal risk since we only keep 1 image)

If you see "no images found" but the repository size is large, there may be orphaned layers from previous incorrect deletions (see Manual Cleanup section).

This ensures the Artifact Registry stays within free tier limits while maintaining the ability to rollback to the most recent deployment.

### Manual Cleanup

If the repository size grows unexpectedly (e.g., due to orphaned layers from previous deletions), you can manually clean up:

**Option 1: Clean up old images (when images exist)**
```bash
# Run image cleanup
./cleanup-artifacts.sh
```

**Option 2: Clean up orphaned layers (when no images exist but size is large)**
```bash
# Delete all orphaned Docker layers
./cleanup-all-orphaned.sh
```

**Understanding Orphaned Layers**:

Docker images are stored as layers (blobs). When images are deleted incorrectly or partially, these layers can remain in the repository even though they're no longer referenced. This causes the repository size to grow without showing any active images.

**Symptoms**:
- Repository size is large (e.g., 1.2GB)
- `gcloud artifacts docker images list` shows no images
- `gcloud artifacts files list` shows many layer files

**Solution**:
1. If no active images exist, use `cleanup-all-orphaned.sh` to delete all orphaned layers
2. If images exist, use `cleanup-artifacts.sh` to delete old images (which will also clean up their layers)
3. The improved CI/CD cleanup script prevents this issue going forward by properly deleting images by digest

## Cloud Run Configuration

### Resource Allocation

```yaml
memory: 2Gi
cpu: 2
timeout: 3600  # 1 hour
max-instances: 1
min-instances: 0
port: 8080
cpu-boost: enabled
```

**Configuration Details**:

- **Memory**: 2GB allocated for handling large financial analysis workloads
- **CPU**: 2 vCPUs for parallel processing
- **Timeout**: 1 hour maximum request duration (for long-running financial analyses)
- **Max Instances**: 1 instance to control costs
- **Min Instances**: 0 instances (scales to zero when idle)
- **CPU Boost**: Enabled for faster cold starts
- **Port**: 8080 (Cloud Run default)

### Service Settings

- **Platform**: Managed (fully managed by Google Cloud)
- **Region**: asia-southeast1
- **Authentication**: Unauthenticated (public access)
- **Service Name**: psx-research-agent

## Local Deployment

For local testing or manual deployment, use the `deploy-local.sh` script:

```bash
# Set required environment variable
export OPENROUTER_API_KEY="your-api-key"

# Run deployment script
./deploy-local.sh
```

**Note**: The script requires:
- `gcloud` CLI installed and authenticated
- Docker installed and running
- `OPENROUTER_API_KEY` environment variable set

The local deployment script performs the same steps as the CI/CD workflow but runs from your local machine.

## Environment Variables

### Required Variables

- **OPENROUTER_API_KEY** - API key for OpenRouter (used for LLM calls in financial analysis and decision-making)

### Setting Environment Variables

**In Cloud Run** (via CI/CD):
```yaml
--set-env-vars OPENROUTER_API_KEY=${{ secrets.OPENROUTER_API_KEY }}
```

**In Local Deployment**:
```bash
export OPENROUTER_API_KEY="your-api-key"
```

**Note**: For production deployments, add `OPENROUTER_API_KEY` to GitHub Secrets (Settings → Secrets and variables → Actions → New repository secret).

## Initial Setup

Before the first deployment, you need to:

1. **Set up Workload Identity Federation** - See [GitHub Secrets Setup Guide](github-secrets-setup.md)
2. **Configure GitHub Secrets**:
   - `GCP_PROJECT_ID` - Your Google Cloud Project ID
   - `WIF_PROVIDER` - Workload Identity Federation provider resource name
   - `OPENROUTER_API_KEY` - OpenRouter API key (for LLM features)

3. **Create Artifact Registry repository** (if not exists):
```bash
gcloud artifacts repositories create psx-research-agent \
  --repository-format=docker \
  --location=asia-southeast1 \
  --project=YOUR_PROJECT_ID \
  --description="PSX Research Agent Docker images"
```

**Note**: If you get "Repository not found" errors, the repository needs to be created first. The cleanup scripts will check for repository existence and provide helpful error messages if it's missing.

4. **Enable required APIs**:
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  --project=YOUR_PROJECT_ID
```

## Troubleshooting

### Deployment Fails with "Permission Denied"

- Verify Workload Identity Federation is set up correctly
- Check service account has required roles (run.admin, artifactregistry.admin)
- Ensure GitHub repository matches the WIF attribute condition

### Health Check Fails

- Verify the `/health` endpoint is accessible
- Check application logs in Cloud Run console
- Ensure port 8080 is correctly configured

### Image Cleanup Not Working

- Check Artifact Registry permissions
- Verify cleanup script has correct image name format
- Check Cloud Run logs for cleanup step output

### Cold Start Timeouts

- Increase `failureThreshold` in startup probe if needed
- Consider enabling `min-instances: 1` to prevent cold starts (costs more)
- Check application startup logs for bottlenecks

### Out of Memory Errors

- Increase memory allocation in Cloud Run configuration
- Check for memory leaks in application code
- Review financial analysis workload memory usage

## Monitoring

### View Deployment Logs

```bash
# View Cloud Run service logs
gcloud run services logs read psx-research-agent \
  --region=asia-southeast1 \
  --project=YOUR_PROJECT_ID
```

### Check Service Status

```bash
# Get service URL
gcloud run services describe psx-research-agent \
  --region=asia-southeast1 \
  --format='value(status.url)'
```

### View GitHub Actions Logs

1. Go to GitHub repository
2. Click **Actions** tab
3. Select the latest workflow run
4. View step-by-step logs

## Cost Optimization

The current configuration is optimized for the free tier:

- **Min instances: 0** - Scales to zero when idle (no cost)
- **Max instances: 1** - Limits concurrent instances
- **Image cleanup** - Keeps only 1 image to stay within 500MB limit
- **CPU boost** - Faster cold starts reduce request duration

**Estimated Monthly Cost**: $0 (within free tier limits)

For higher traffic, consider:
- Increasing `max-instances` for better concurrency
- Setting `min-instances: 1` to eliminate cold starts (increases cost)
- Using Cloud Run's request-based pricing model

## Additional Resources

- [GitHub Secrets Setup Guide](github-secrets-setup.md) - Initial WIF configuration
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)

