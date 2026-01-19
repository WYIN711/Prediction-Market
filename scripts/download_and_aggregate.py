#!/usr/bin/env python3
"""
Download trade data from GitHub releases and aggregate incrementally.
This script processes files one at a time to minimize disk usage.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


def get_release_tags(repo: str, limit: int = 200) -> List[str]:
    """Get list of data release tags from GitHub."""
    result = subprocess.run(
        ["gh", "release", "list", "--repo", repo, "--limit", str(limit),
         "--json", "tagName", "-q", ".[].tagName"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error listing releases: {result.stderr}")
        return []
    
    tags = [t for t in result.stdout.strip().split("\n") if t.startswith("data-")]
    return sorted(tags, reverse=True)


def download_and_extract(repo: str, tag: str, output_dir: Path) -> Path | None:
    """Download and extract a single release, return path to JSON file."""
    date_str = tag.replace("data-", "")
    archive_name = f"kalshi_trades_{date_str}.tar.gz"
    json_file = output_dir / f"{date_str}.json"
    
    # Skip if already exists
    if json_file.exists():
        return json_file
    
    # Download
    result = subprocess.run(
        ["gh", "release", "download", tag, "-p", archive_name, "-D", str(output_dir), "--repo", repo],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Failed to download {tag}: {result.stderr}")
        return None
    
    # Extract
    archive_path = output_dir / archive_name
    result = subprocess.run(
        ["tar", "-xzf", str(archive_path), "-C", str(output_dir)],
        capture_output=True, text=True
    )
    
    # Clean up archive
    archive_path.unlink(missing_ok=True)
    
    # Remove macOS resource fork files
    for rf in output_dir.glob("._*.json"):
        rf.unlink(missing_ok=True)
    
    if json_file.exists():
        return json_file
    return None


def process_single_file(file_path: Path) -> Tuple[pd.Timestamp, int, Dict[str, int]]:
    """Process a single JSON file, return date, total volume, and category volumes."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  Warning: Skipping corrupted file {file_path}: {e}")
        return pd.to_datetime(file_path.stem), 0, {}
    
    # Extract trades
    if isinstance(payload, dict):
        date_str = payload.get("date", file_path.stem)
        trades = payload.get("trades", [])
    elif isinstance(payload, list):
        trades = payload
        date_str = trades[0].get("date", file_path.stem) if trades else file_path.stem
    else:
        return pd.to_datetime(file_path.stem), 0, {}
    
    date = pd.to_datetime(date_str)
    
    total_volume = 0
    category_totals: Dict[str, int] = {}
    
    for trade in trades:
        volume = int(trade.get("count") or trade.get("contracts_traded") or 0)
        if volume <= 0:
            continue
        total_volume += volume
        
        ticker = str(trade.get("ticker") or trade.get("ticker_name") or trade.get("report_ticker") or "")
        category = classify_ticker(ticker)
        category_totals[category] = category_totals.get(category, 0) + volume
    
    return date, total_volume, category_totals


def classify_ticker(ticker: str) -> str:
    """Classify a ticker into a market category."""
    upper_ticker = ticker.upper()
    prefix = upper_ticker.split("-", 1)[0]

    def starts_with(prefixes: tuple) -> bool:
        return any(prefix.startswith(p) for p in prefixes)

    def contains(keywords: tuple) -> bool:
        return any(keyword in upper_ticker for keyword in keywords)

    if starts_with(("KXNFL", "KXSB", "KXMVENFL")):
        return "NFL Football"
    if starts_with(("KXNCAAF", "KXCFB", "KXCOLLFB")):
        return "NCAA Football"
    if starts_with(("KXNBA", "KXMVENBA")):
        return "NBA Basketball"
    if starts_with(("KXNCAAM", "KXNCAAB", "KXMARCH", "KXCBB")):
        return "NCAA Basketball"
    if starts_with(("KXMLB",)):
        return "MLB Baseball"
    if starts_with(("KXNHL",)):
        return "NHL Hockey"
    if starts_with(("KXSOC", "KXEPL", "KXMLS", "KXUCL", "KXWC")):
        return "Soccer"
    if starts_with(("KXPGA", "KXGOLF")):
        return "Golf"
    if starts_with(("KXNASCAR", "KXF1", "KXINDY")):
        return "Motorsports"
    if starts_with(("KXUFC", "KXMMA", "KXBOX")):
        return "Combat Sports"
    if starts_with(("KXTEN", "KXWIMB", "KXUSO", "KXAUS")):
        return "Tennis"

    if starts_with(("INX", "INXD", "INXU")):
        return "S&P 500"
    if starts_with(("NASDAQ", "NDX", "COMP")):
        return "NASDAQ"
    if starts_with(("DJIA", "DJI")):
        return "Dow Jones"
    if starts_with(("BTC", "BITCOIN")):
        return "Bitcoin"
    if starts_with(("ETH", "ETHER")):
        return "Ethereum"
    if starts_with(("CPI",)):
        return "CPI / Inflation"
    if starts_with(("FED", "FOMC")):
        return "Fed / Interest Rates"

    if contains(("TRUMP", "BIDEN", "HARRIS", "ELECT", "PRES", "SENAT", "HOUSE", "GOP", "DEM")):
        return "Politics"
    if contains(("WEATHER", "TEMP", "HURRIC", "SNOW")):
        return "Weather"

    return "Other"


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "WYIN711/Prediction-Market")
    days_back = int(os.environ.get("DAYS_BACK", "90"))
    output_dir = Path(os.environ.get("KALSHI_DATA_DIR", "data/kalshi_trades"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading and processing last {days_back} days of data...")
    
    # Get release tags
    tags = get_release_tags(repo)
    if not tags:
        print("No data releases found.")
        sys.exit(1)
    
    # Filter to requested number of days
    tags = tags[:days_back]
    print(f"Found {len(tags)} releases to process")
    
    # Process files one at a time
    daily_totals: List[Tuple[pd.Timestamp, int]] = []
    category_records: List[dict] = []
    
    for i, tag in enumerate(tags):
        print(f"[{i+1}/{len(tags)}] Processing {tag}...")
        
        # Download and extract
        json_file = download_and_extract(repo, tag, output_dir)
        if json_file is None:
            continue
        
        # Process
        date, total_volume, category_totals = process_single_file(json_file)
        
        daily_totals.append((date, total_volume))
        for category, volume in category_totals.items():
            category_records.append({"date": date, "category": category, "volume": volume})
        
        # Delete file to save space
        json_file.unlink(missing_ok=True)
        
        # Also remove any macOS resource fork files
        for rf in output_dir.glob("._*.json"):
            rf.unlink(missing_ok=True)
    
    # Create DataFrames
    daily_df = pd.DataFrame(daily_totals, columns=["date", "total_volume"])
    daily_df = daily_df.sort_values("date").reset_index(drop=True)
    
    category_df = pd.DataFrame(category_records)
    if not category_df.empty:
        category_df = category_df.sort_values("date").reset_index(drop=True)
    
    # Save aggregated data
    daily_df.to_csv(output_dir / "aggregated_daily.csv", index=False)
    category_df.to_csv(output_dir / "aggregated_category.csv", index=False)
    
    print(f"\n✅ Processed {len(daily_totals)} days of data")
    print(f"   Daily totals saved to: {output_dir / 'aggregated_daily.csv'}")
    print(f"   Category data saved to: {output_dir / 'aggregated_category.csv'}")


if __name__ == "__main__":
    main()
