#!/bin/zsh
set -euo pipefail

WORKDIR="/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker"
LOGDIR="${WORKDIR}/logs"

mkdir -p "${LOGDIR}"

cd "${WORKDIR}"
/usr/bin/env python3 "${WORKDIR}/scripts/download_kalshi_trades.py" --max-workers 4 >> "${LOGDIR}/trade_sync.log" 2>&1











