#!/bin/bash
set -euo pipefail

# Upload historical Kalshi trade data to GitHub Releases
# Run this locally to upload your existing data

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/data/kalshi_trades}"
REPO="${GITHUB_REPO:-WYIN711/Prediction-Market}"

# Check for gh CLI
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is required but not installed."
    echo "Install with: brew install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

echo "=============================================="
echo "Uploading Historical Data to GitHub Releases"
echo "=============================================="
echo ""
echo "Repository: $REPO"
echo "Data directory: $DATA_DIR"
echo ""

# Count files
FILE_COUNT=$(ls -1 "$DATA_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "Found $FILE_COUNT JSON files to upload"
echo ""

if [[ "$FILE_COUNT" -eq 0 ]]; then
    echo "No files to upload."
    exit 0
fi

# Confirm
read -p "This will create $FILE_COUNT releases. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Process files
UPLOADED=0
SKIPPED=0
FAILED=0

cd "$DATA_DIR"

for json_file in *.json; do
    if [[ ! -f "$json_file" ]]; then
        continue
    fi
    
    DATE_STR="${json_file%.json}"
    TAG_NAME="data-${DATE_STR}"
    ARCHIVE_NAME="kalshi_trades_${DATE_STR}.tar.gz"
    
    # Check if release already exists
    if gh release view "$TAG_NAME" --repo "$REPO" &> /dev/null; then
        echo "[$DATE_STR] Release already exists, skipping..."
        ((SKIPPED++))
        continue
    fi
    
    echo "[$DATE_STR] Compressing..."
    tar -czf "$ARCHIVE_NAME" "$json_file"
    
    ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
    echo "[$DATE_STR] Archive size: $ARCHIVE_SIZE"
    
    echo "[$DATE_STR] Creating release and uploading..."
    if gh release create "$TAG_NAME" \
        --repo "$REPO" \
        --title "Trade Data: ${DATE_STR}" \
        --notes "Kalshi trade data for ${DATE_STR}" \
        "$ARCHIVE_NAME"; then
        ((UPLOADED++))
        echo "[$DATE_STR] ✓ Uploaded successfully"
    else
        ((FAILED++))
        echo "[$DATE_STR] ✗ Failed to upload"
    fi
    
    # Clean up archive
    rm -f "$ARCHIVE_NAME"
    
    # Rate limit protection
    sleep 1
done

echo ""
echo "=============================================="
echo "Upload Complete"
echo "=============================================="
echo "Uploaded: $UPLOADED"
echo "Skipped (already exists): $SKIPPED"
echo "Failed: $FAILED"
