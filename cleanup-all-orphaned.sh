#!/bin/bash
# Delete all orphaned Docker layers from Artifact Registry
# Use this when there are no active images and you want to clean up orphaned layers

# Don't use set -e as we want to handle errors manually
set -u  # Only fail on undefined variables

PROJECT_ID="gen-lang-client-0867784382"
REPOSITORY_NAME="psx-research-agent"
REGION="asia-southeast1"

echo "🔍 Checking repository status..."
if ! gcloud artifacts repositories describe ${REPOSITORY_NAME} \
  --location=${REGION} \
  --project=${PROJECT_ID} >/dev/null 2>&1; then
  echo "❌ Repository '${REPOSITORY_NAME}' not found!"
  echo "   Create it with:"
  echo "   gcloud artifacts repositories create ${REPOSITORY_NAME} \\"
  echo "     --repository-format=docker \\"
  echo "     --location=${REGION} \\"
  echo "     --project=${PROJECT_ID}"
  exit 1
fi

REPO_SIZE=$(gcloud artifacts repositories describe ${REPOSITORY_NAME} \
  --location=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(repositorySize)" 2>/dev/null || echo "unknown")
echo "Current repository size: ${REPO_SIZE}"
echo ""

echo "📦 Listing all files in repository..."
# Use a simple approach - gcloud should return all files by default
# But we'll use --filter to ensure we get everything
gcloud artifacts files list \
  --project=${PROJECT_ID} \
  --location=${REGION} \
  --repository=${REPOSITORY_NAME} \
  --format="value(name)" \
  --filter="" > /tmp/all_files.txt 2>/tmp/gcloud_list_errors.txt || {
  echo "⚠️  Warning: Error during file listing. Trying without filter..."
  cat /tmp/gcloud_list_errors.txt 2>/dev/null || true
  # Try without filter
  gcloud artifacts files list \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --repository=${REPOSITORY_NAME} \
    --format="value(name)" > /tmp/all_files.txt 2>/tmp/gcloud_list_errors.txt || {
    echo "❌ Failed to list files. Error:"
    cat /tmp/gcloud_list_errors.txt
    rm -f /tmp/all_files.txt /tmp/gcloud_list_errors.txt
    exit 1
  }
}

# Clean up error file
rm -f /tmp/gcloud_list_errors.txt

# Remove any empty lines or error messages that might have been captured
sed -i '/^$/d' /tmp/all_files.txt
sed -i '/^ERROR:/d' /tmp/all_files.txt
sed -i '/^WARNING:/d' /tmp/all_files.txt

TOTAL_FILES=$(wc -l < /tmp/all_files.txt | tr -d ' ')
echo "Total files found: ${TOTAL_FILES}"

# Debug: Show actual file contents to verify
if [ "$TOTAL_FILES" -gt 0 ]; then
  echo "Sample files (first 5):"
  head -5 /tmp/all_files.txt | nl -nln | while IFS= read -r line; do
    file_path=$(echo "$line" | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')
    if [ -n "$file_path" ]; then
      echo "  - $(basename "$file_path" 2>/dev/null || echo "$file_path")"
    fi
  done
  if [ "$TOTAL_FILES" -gt 5 ]; then
    echo "  ... and $((TOTAL_FILES - 5)) more"
  fi
  echo ""
  echo "📋 Verifying file list (showing first 10 lines raw):"
  head -10 /tmp/all_files.txt | cat -A
  echo ""
fi
echo ""

if [ "$TOTAL_FILES" -eq 0 ]; then
  echo "No files to delete."
  rm -f /tmp/all_files.txt
  exit 0
fi

echo "⚠️  WARNING: This will delete ALL ${TOTAL_FILES} files from the repository."
echo "   Since there are no active images, these are all orphaned layers."
echo ""
read -p "Do you want to proceed? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  echo "Cleanup cancelled."
  rm -f /tmp/all_files.txt
  exit 0
fi

echo ""
echo "🧹 Deleting orphaned layers..."
DELETED=0
FAILED=0
PROCESSED=0

# Ensure we read all lines, including those without newlines at the end
# Filter out any error/warning lines that might have been captured
while IFS= read -r file_path || [ -n "$file_path" ]; do
  # Skip empty lines and error messages
  if [ -z "$file_path" ] || [[ "$file_path" =~ ^(ERROR|WARNING) ]]; then
    continue
  fi
  
  # Skip if it doesn't look like a valid file path
  if [[ ! "$file_path" =~ ^[^[:space:]]+$ ]]; then
    continue
  fi
  
  ((PROCESSED++)) || true
  file_name=$(basename "$file_path" 2>/dev/null || echo "$file_path")
  printf "[%d/%d] Deleting: %s ... " "$PROCESSED" "$TOTAL_FILES" "$file_name"
  
  DELETE_OUTPUT=$(gcloud artifacts files delete "${file_path}" \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --repository=${REPOSITORY_NAME} \
    --quiet 2>&1)
  DELETE_EXIT=$?
  
  if [ $DELETE_EXIT -eq 0 ]; then
    echo "✅"
    ((DELETED++)) || true
  else
    # Check if it's a "not found" error (already deleted) or a real error
    if echo "$DELETE_OUTPUT" | grep -qi "not found\|already deleted\|404"; then
      echo "⚠️  (already deleted)"
    else
      echo "❌ Error: $(echo "$DELETE_OUTPUT" | head -1)"
    fi
    ((FAILED++)) || true
  fi
done < /tmp/all_files.txt

echo ""
echo "Processed: ${PROCESSED} files"

rm -f /tmp/all_files.txt

echo ""
echo "✅ Cleanup complete!"
echo "   Successfully deleted: ${DELETED} files"
echo "   Failed/Skipped: ${FAILED} files"
echo ""
echo "📊 Checking repository size after cleanup..."
sleep 5  # Wait for cleanup to propagate
NEW_REPO_SIZE=$(gcloud artifacts repositories describe ${REPOSITORY_NAME} \
  --location=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(repositorySize)" 2>/dev/null || echo "unknown")

echo "New repository size: ${NEW_REPO_SIZE}"
echo ""
echo "Note: Repository size may take a few minutes to fully update."
