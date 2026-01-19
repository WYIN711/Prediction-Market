#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python interpreter not found. Set PYTHON_BIN explicitly." >&2
    exit 1
  fi
fi

OUTPUT_BASE="$ROOT_DIR/analysis/runs"
OUTPUT_DIR="$ROOT_DIR/analysis"

DATE_STR="$(date +%Y-%m-%d)"
RUN_DIR="$OUTPUT_BASE/$DATE_STR"

# Ensure unique directory for repeated runs on the same day
if [[ -d "$RUN_DIR" ]]; then
  suffix=1
  while [[ -d "${RUN_DIR}_$suffix" ]]; do
    ((suffix++))
  done
  RUN_DIR="${RUN_DIR}_$suffix"
fi

mkdir -p "$RUN_DIR"

# Clear proxy settings to avoid connectivity issues
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export NO_PROXY=""

cd "$ROOT_DIR"
export KALSHI_ROOT_DIR="$ROOT_DIR"

"$PYTHON_BIN" "$ROOT_DIR/analysis/generate_all_plots.py"

outputs=(
  "7d_rolling_total_volume.png"
  "top_10_market_types_7d_ma.png"
  "daily_total_volume_python.csv"
  "daily_category_volume.csv"
)

for file in "${outputs[@]}"; do
  src="$OUTPUT_DIR/$file"
  dest="$RUN_DIR/$file"
  if [[ -f "$src" ]]; then
    mv "$src" "$dest"
  else
    echo "Warning: expected output $file not found at $src"
  fi
done

echo "Plots saved to $RUN_DIR"

