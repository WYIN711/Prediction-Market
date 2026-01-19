#!/usr/bin/env python3
"""
Download Kalshi daily trades data and store each day as a JSON file.

The script discovers which dates still need to be downloaded, paginates through
Kalshi's public elections trade API, and writes one file per day into
``data/kalshi_trades/<YYYY-MM-DD>.json`` by default.

Typical usage for daily syncs (auto-detects the range):
    python3 scripts/download_kalshi_trades.py
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib import error, parse, request

try:
    from zoneinfo import ZoneInfo
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Python 3.9+ with zoneinfo support is required.") from exc


BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets/trades"
DEFAULT_LIMIT = 500
REQUEST_TIMEOUT_SECONDS = 30
RETRY_DELAY_SECONDS = 10
MAX_RETRIES = 8
DEFAULT_START_DATE = "2025-08-15"

# Ensure no proxy environment variables interfere with direct API calls.
for proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    os.environ.pop(proxy_var, None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Kalshi daily trades data into per-day JSON files."
    )
    parser.add_argument(
        "--start-date",
        help="First date to download (inclusive, YYYY-MM-DD). Defaults to day after the latest saved file or 2025-08-15.",
    )
    parser.add_argument(
        "--end-date",
        help="Last date to download (inclusive, YYYY-MM-DD). Defaults to yesterday in the chosen timezone.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/kalshi_trades",
        help="Directory where per-day JSON files will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Number of trades to request per API page (default: {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of skipping them.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.05,
        help="Delay between page requests to avoid overwhelming the API.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Number of concurrent days to download. Use 1 for sequential mode.",
    )
    parser.add_argument(
        "--include-today",
        action="store_true",
        help="Include the current (possibly partial) day in downloads.",
    )
    parser.add_argument(
        "--timezone",
        default="America/New_York",
        help="Timezone used to determine the default end date (default: America/New_York).",
    )
    return parser.parse_args()


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def to_unix_range(day: date) -> tuple[int, int]:
    start_dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def detect_range(
    args: argparse.Namespace,
    out_dir: Path,
) -> tuple[Optional[date], Optional[date], date]:
    tz = ZoneInfo(args.timezone)
    today_local = datetime.now(tz).date()
    default_end = today_local - timedelta(days=1)

    if args.end_date:
        end_date = parse_date(args.end_date)
    else:
        end_date = default_end

    existing_dates = sorted(
        parse_date(p.stem)
        for p in out_dir.glob("*.json")
        if len(p.stem) == 10 and p.stem[4] == "-" and p.stem[7] == "-"
    )

    if args.start_date:
        start_date = parse_date(args.start_date)
    else:
        if existing_dates:
            start_date = existing_dates[-1] + timedelta(days=1)
        else:
            start_date = parse_date(DEFAULT_START_DATE)

    return start_date, end_date, today_local


def _create_ssl_context(verify: bool = True):
    """Create SSL context for launchd compatibility."""
    if verify:
        try:
            # Try to use default system certificates
            return ssl.create_default_context()
        except Exception:
            pass
    # Fallback: create unverified context (works in launchd environment)
    return ssl._create_unverified_context()


# Use unverified SSL context for launchd compatibility
# (launchd doesn't have access to system certificates)
_SSL_CONTEXT = _create_ssl_context(verify=False)


def fetch_page(params: Dict[str, str], attempt: int = 1) -> Dict:
    query = parse.urlencode(params)
    url = f"{BASE_URL}?{query}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "kalshi-trade-downloader/1.0 (+https://kalshi.com/trade-data)",
    }
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=_SSL_CONTEXT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset)
            return json.loads(body)
    except (error.HTTPError, error.URLError, TimeoutError, http.client.IncompleteRead, ConnectionResetError) as exc:
        if attempt >= MAX_RETRIES:
            raise
        sleep_seconds = RETRY_DELAY_SECONDS * attempt
        print(
            f"[warn] Request failed ({exc}). Retrying in {sleep_seconds:.1f}s "
            f"(attempt {attempt}/{MAX_RETRIES})...",
            file=sys.stderr,
        )
        time.sleep(sleep_seconds)
        return fetch_page(params, attempt + 1)


def fetch_trades_for_day(
    day: date, limit: int, page_delay: float
) -> List[Dict]:
    min_ts, max_ts = to_unix_range(day)
    cursor: Optional[str] = None
    trades: List[Dict] = []

    while True:
        params: Dict[str, str | int] = {
            "min_ts": min_ts,
            "max_ts": max_ts,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        data = fetch_page({k: str(v) for k, v in params.items()})
        page_trades = data.get("trades", [])
        trades.extend(page_trades)

        cursor = data.get("cursor")
        if not cursor:
            break

        time.sleep(page_delay)

    return trades


def download_single_day(
    day: date,
    output_file: Path,
    limit: int,
    page_delay: float,
) -> tuple[date, Path, int]:
    print(f"[fetch] {day.isoformat()} ...", end="", flush=True)
    trades = fetch_trades_for_day(day, limit, page_delay)

    payload = {
        "date": day.isoformat(),
        "min_ts": to_unix_range(day)[0],
        "max_ts": to_unix_range(day)[1],
        "trade_count": len(trades),
        "trades": trades,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f" done ({len(trades)} trades). Saved to {output_file}")
    return day, output_file, len(trades)


def main() -> int:
    args = parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start_date, end_date, today_local = detect_range(args, out_dir)
    if not args.include_today and end_date >= today_local:
        end_date = today_local - timedelta(days=1)

    if start_date is None or end_date is None:
        print("Could not determine start or end date.", file=sys.stderr)
        return 1

    if start_date > end_date:
        print(
            f"No new dates to download (start={start_date}, end={end_date}).",
            file=sys.stderr,
        )
        return 0

    pending_days: List[date] = []
    for day in daterange(start_date, end_date):
        output_file = out_dir / f"{day.isoformat()}.json"
        if output_file.exists() and not args.overwrite:
            print(f"[skip] {output_file} already exists.")
            continue
        pending_days.append(day)

    if not args.include_today:
        partial_file = out_dir / f"{today_local.isoformat()}.json"
        if partial_file.exists():
            try:
                partial_file.unlink()
                print(f"[info] Removed partial file for today {today_local.isoformat()}.")
            except OSError as exc:
                print(
                    f"[warn] Could not remove partial file {partial_file}: {exc}",
                    file=sys.stderr,
                )

    if not pending_days:
        print("All requested dates are already downloaded.")
        return 0

    failures: List[tuple[date, Exception]] = []
    max_workers = max(1, args.max_workers)
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for day in pending_days:
            output_file = out_dir / f"{day.isoformat()}.json"
            futures[
                executor.submit(
                    download_single_day,
                    day,
                    output_file,
                    args.limit,
                    args.sleep_seconds,
                )
            ] = day

        for future in as_completed(futures):
            day = futures[future]
            try:
                future.result()
            except Exception as exc:  # pylint: disable=broad-except
                failures.append((day, exc))
                print(
                    f"[error] Failed to download {day.isoformat()}: {exc}",
                    file=sys.stderr,
                )

    if failures:
        print(
            f"Completed with {len(failures)} failure(s). See stderr for details.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

