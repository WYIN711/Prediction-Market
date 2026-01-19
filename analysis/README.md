# Kalshi Trading Volume Analysis

This folder contains utilities for summarising downloaded Kalshi trade data and producing key monitoring charts.

## Prerequisites

- Python virtual environment at `.venv/` with `pandas` and `matplotlib`.
- Runtimes expect the raw daily JSON files under `data/kalshi_trades`.
- Optional: cron (already configured) for scheduled updates.

## Scripts

- `compute_volume.py`  
  Aggregates daily trade counts over all markets, exports `daily_total_volume_python.csv`, and renders `7d_rolling_total_volume.png`.

- `market_type_trends.py`  
  Classifies trades into broad market categories (NFL, NCAA football, NBA, MLB, Soccer, Tennis, NHL, Cryptocurrency, Politics/Elections, Other) and builds `daily_category_volume.csv` plus `top_10_market_types_7d_ma.png`.

- `update_plots.sh`  
  Wrapper that runs both Python scripts inside the project venv, then archives the fresh CSV/PNG outputs into `analysis/runs/<YYYY-MM-DD>/`. Existing copies in `analysis/` are removed to keep the parent clean, and proxy variables are cleared before each run.

## Generated Outputs

On each execution you will find:

- `analysis/runs/<date>/7d_rolling_total_volume.png`
- `analysis/runs/<date>/top_10_market_types_7d_ma.png`
- `analysis/runs/<date>/daily_total_volume_python.csv`
- `analysis/runs/<date>/daily_category_volume.csv`

Each subfolder reflects one run; reruns on the same date append `_1`, `_2`, … to avoid overwriting.

## Usage

### Manual refresh

From the project root:

```bash
./analysis/update_plots.sh
```

The script assumes the virtual environment at `.venv/` is already populated. If you need to recreate it:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install pandas matplotlib
```

### Scheduled updates

A cron job is registered under the current user to run every Monday and Thursday at 08:00 local time:

```
0 8 * * 1,4 cd "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker" && ./analysis/update_plots.sh >> "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/analysis/logs/update_plots.log" 2>&1
```

To adjust or remove the schedule, run `crontab -e`.

### Log files

Execution output is appended to `analysis/logs/update_plots.log`. Inspect this log if the cron job does not produce a new dated folder.

## Extending the workflow

- Drop additional classification rules into `market_type_trends.py` -> `classify_ticker`.
- Add new visualisations by extending `update_plots.sh` with extra scripts and copy statements.
- Ensure new artifacts are copied into the dated run directory and the originals removed from the parent folder to keep the workspace tidy.

