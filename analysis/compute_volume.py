from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd


DATA_DIR = Path(
    "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/data/kalshi_trades"
)
OUTPUT_DIR = Path(
    "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/analysis"
)


@dataclass
class DailyVolume:
    date: pd.Timestamp
    total_volume: int


def read_daily_volume(file_path: Path) -> DailyVolume:
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    date = pd.to_datetime(payload["date"])
    trades: Iterable[dict] = payload.get("trades", [])
    total_volume = int(sum(trade.get("count", 0) for trade in trades))
    return DailyVolume(date=date, total_volume=total_volume)


def collect_daily_volumes(files: Iterable[Path]) -> pd.DataFrame:
    volumes: List[DailyVolume] = [read_daily_volume(path) for path in files]
    df = pd.DataFrame([vars(item) for item in volumes])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def format_millions(x: float, pos: int) -> str:
    return f"{x / 1e6:,.1f}M"


def plot_rolling_volume(df: pd.DataFrame, window: int = 7) -> Path:
    df = df.copy()
    df["rolling_volume"] = df["total_volume"].rolling(window=window, min_periods=1).sum()

    fig, ax = plt.subplots(figsize=(14, 9))
    ax.plot(df["date"], df["rolling_volume"], color="#0b3d91", linewidth=2)
    ax.scatter(df["date"], df["rolling_volume"], color="#0b3d91", s=18)

    ax.set_title(f"{window}-Day Rolling Total Trading Volume")
    ax.set_xlabel("Date")
    ax.set_ylabel(f"{window}-Day Total Volume (Contracts)")

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_millions))
    ax.grid(color="0.85", linestyle="-", linewidth=0.8, alpha=0.8)

    fig.autofmt_xdate()
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{window}d_rolling_total_volume.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def main() -> None:
    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No trade files found in {DATA_DIR}")

    df = collect_daily_volumes(files)

    rolling_plot_path = plot_rolling_volume(df, window=7)
    daily_csv_path = OUTPUT_DIR / "daily_total_volume_python.csv"
    df.to_csv(daily_csv_path, index=False, date_format="%Y-%m-%d")

    print("Daily totals saved to:", daily_csv_path)
    print("7-day rolling total chart saved to:", rolling_plot_path)


if __name__ == "__main__":
    main()

