#!/usr/bin/env python3
"""Fetch Polymarket events that meet specific criteria and save to Excel."""

import json
import os
import requests
import pandas as pd
from datetime import datetime, timezone
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from pathlib import Path


def parse_iso_datetime(date_str):
    """Parse ISO8601 strings safely; return None on failure."""
    if not date_str:
        return None
    try:
        return date_parser.isoparse(date_str)
    except (ValueError, TypeError):
        return None


def fetch_markets():
    url = "https://gamma-api.polymarket.com/events"
    all_events = []
    offset = 0
    limit = 100

    print("Fetching events...")
    while True:
        params = {
            "volume_num_min": 1000000,
            "limit": limit,
            "offset": offset,
            "closed": "false"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            all_events.extend(data)
            print(f"Fetched {len(data)} events (Total: {len(all_events)})")

            if len(data) < limit:
                break

            offset += limit

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break

    now_utc = datetime.now(timezone.utc)
    cutoff_date = now_utc + relativedelta(months=6)

    print(f"\nFound {len(all_events)} total events with volume > 1M (event-level). Filtering to events ending within the next 6 months, then markets for volume > 1M and probability in (95%, 99%) or (1%, 5%)...\n")

    match_count = 0
    all_matches = []

    for event in all_events:
        title = event.get('title', 'Unknown Title')
        event_end_date_str = event.get('endDate')
        event_end_date = parse_iso_datetime(event_end_date_str)

        # Skip events without a valid end date or those outside the 6-month window
        if not event_end_date or event_end_date < now_utc or event_end_date > cutoff_date:
            continue

        markets = event.get('markets', [])

        for market in markets:
            # Check if market is closed or resolved
            if market.get('closed'):
                continue

            # Strict volume check on the market itself
            volume = market.get('volumeNum', 0)
            if volume < 1000000:
                continue

            outcome_prices = market.get('outcomePrices')
            outcomes = market.get('outcomes')

            if not outcome_prices or not outcomes:
                continue

            try:
                # outcomePrices might be a JSON string
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)

                # outcomes might also be a JSON string
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)

                # Convert prices to floats
                prices = [float(p) for p in outcome_prices]
            except (ValueError, json.JSONDecodeError):
                continue

            # Check if any price is in (0.95, 0.99) OR (0.01, 0.05)
            for i, price in enumerate(prices):
                if (price > 0.95 and price < 0.99) or (price > 0.01 and price < 0.05):
                    match_count += 1
                    outcome_name = outcomes[i] if i < len(outcomes) else f"Outcome {i}"

                    market_end_date_str = market.get('endDate') or market.get('endDateIso')

                    print(f"Event: {title}")
                    print(f"Market: {market.get('question', 'N/A')}")
                    print(f"Outcome: {outcome_name}")
                    print(f"Probability: {price * 100:.1f}%")
                    print(f"Volume: ${volume:,.2f}")
                    if event_end_date_str:
                        print(f"Event End: {event_end_date_str}")
                    if market_end_date_str:
                        print(f"Market End: {market_end_date_str}")
                    print("-" * 40)

                    all_matches.append({
                        "Event": title,
                        "Market": market.get('question', 'N/A'),
                        "Outcome": outcome_name,
                        "Probability": price,
                        "Volume": volume,
                        "EventEndDate": event_end_date_str,
                        "MarketEndDate": market_end_date_str
                    })

    print(f"\nTotal matches found: {match_count}")

    # Determine output directory (docs/ for GitHub Pages)
    script_dir = Path(__file__).parent
    docs_dir = script_dir / "docs"
    docs_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"polymarket_data_{date_str}.xlsx"
    filepath = docs_dir / filename

    if all_matches:
        df = pd.DataFrame(all_matches)
        df.to_excel(filepath, index=False)
        print(f"Data saved to {filepath}")
    else:
        # Create empty Excel file even if no matches
        df = pd.DataFrame(columns=["Event", "Market", "Outcome", "Probability", "Volume", "EventEndDate", "MarketEndDate"])
        df.to_excel(filepath, index=False)
        print(f"No matches found, created empty file at {filepath}")

    # Generate index.html for GitHub Pages
    generate_index_html(docs_dir)

    # Output for GitHub Actions
    print(f"::set-output name=match_count::{match_count}")
    print(f"::set-output name=filename::{filename}")

    return match_count, filename


def generate_index_html(docs_dir: Path):
    """Generate an index.html listing all Excel files."""
    excel_files = sorted(docs_dir.glob("polymarket_data_*.xlsx"), reverse=True)

    file_list_html = ""
    for f in excel_files:
        date_part = f.stem.replace("polymarket_data_", "")
        file_list_html += f'        <li><a href="{f.name}">{date_part}</a></li>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Weekly Reports</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #333; }}
        ul {{ list-style: none; padding: 0; }}
        li {{
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-size: 18px;
        }}
        a:hover {{ text-decoration: underline; }}
        .description {{
            color: #666;
            font-size: 14px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>Polymarket Weekly Reports</h1>
    <p class="description">
        Markets with volume &gt; $1M and probability between 95-99% or 1-5%,
        ending within 6 months.
    </p>
    <ul>
{file_list_html}    </ul>
    <p class="description">Updated every Saturday at 10:00 AM HKT</p>
</body>
</html>
"""

    index_path = docs_dir / "index.html"
    index_path.write_text(html_content)
    print(f"Generated {index_path}")


if __name__ == "__main__":
    fetch_markets()
