from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple, Union

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

DATA_DIR = Path(
    "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/data/kalshi_trades"
)
OUTPUT_DIR = Path(
    "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/analysis"
)


def load_trade_payload(file_path: Path) -> Tuple[pd.Timestamp, Iterable[dict]]:
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    date_str: Union[str, None] = None
    trades: Iterable[dict]

    if isinstance(payload, dict):
        date_str = payload.get("date")
        trades = payload.get("trades", [])
    elif isinstance(payload, list):
        trades = payload
        if trades:
            date_str = trades[0].get("date")
    else:
        raise ValueError(f"Unsupported payload structure in {file_path}")

    if not date_str:
        date_str = file_path.stem

    date = pd.to_datetime(date_str)
    return date, trades


def trade_ticker(trade: Dict[str, Any]) -> str:
    return str(
        trade.get("ticker")
        or trade.get("ticker_name")
        or trade.get("report_ticker")
        or ""
    )


def trade_volume(trade: Dict[str, Any]) -> int:
    return int(trade.get("count") or trade.get("contracts_traded") or 0)


def filter_complete_days(df: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp.today().normalize()
    filtered = df[df["date"] < today]
    if not filtered.empty:
        return filtered
    return df


def classify_ticker(ticker: str) -> str:
    """Map a Kalshi ticker to a high-level market category."""

    upper_ticker = ticker.upper()
    prefix = upper_ticker.split("-", 1)[0]

    def starts_with(prefixes: tuple[str, ...]) -> bool:
        return any(prefix.startswith(p) for p in prefixes)

    def contains(keywords: tuple[str, ...]) -> bool:
        return any(keyword in upper_ticker for keyword in keywords)

    if starts_with(("KXNFL", "KXSB", "KXMVENFL")):
        return "NFL Football"
    if starts_with(("KXNCAAF", "KXCFB", "KXCOLLFB")):
        return "NCAA Football"
    if starts_with(("KXMLB", "KXBASEBALL")):
        return "MLB Baseball"
    if starts_with(("KXNBA", "KXWNBA", "KXNCAAMB")):
        return "NBA Basketball"
    if starts_with(("KXNHL", "KXHOCKEY")):
        return "NHL Hockey"
    if starts_with(
        (
            "KXEPL",
            "KXUCL",
            "KXLALIGA",
            "KXSERIA",
            "KXBUNDES",
            "KXUEL",
            "KXCARABAO",
            "KXFA",
            "KXPREMIERLEAGUE",
            "KXMLS",
            "KXSOC",
            "KXCHAMPIONS",
            "KXUSLC",
            "KXSERIB",
            "KXCOPA",
            "KXSAUDI",
        )
    ) or contains(
        ("SOCC", "LIGA", "SERIE", "UEFA", "CHAMPIONS", "PREMIER", "MLS", "FA CUP")
    ):
        return "Soccer"
    if starts_with(
        (
            "KXATP",
            "KXWTA",
            "KXUSO",
            "KXAUS",
            "KXROL",
            "KXWIM",
            "KXTENNIS",
            "KXUSOMEN",
            "KXUSOWOMEN",
        )
    ) or contains(("TENNIS", "ROLAND GARROS", "WIMBLEDON")):
        return "Tennis"
    if starts_with(
        (
            "KXBTC",
            "KXETH",
            "KXSOL",
            "KXCRYPTO",
            "KXETHD",
            "KXETHM",
            "KXETHF",
            "KXBTCM",
            "KXETHMAX",
        )
    ) or contains(("CRYPTO", "BITCOIN", "ETHEREUM", "SOLANA")):
        return "Cryptocurrency"
    if contains(
        (
            "ELECTION",
            "SENATE",
            "HOUSE",
            "MAYOR",
            "GOV",
            "TRUMP",
            "BIDEN",
            "PRIMARY",
            "PRES",
            "CONGRESS",
            "BALLOT",
            "GOP",
            "DEM",
            "RUNOFF",
            "VP",
        )
    ):
        return "Politics/Elections"

    return "Other"


def load_daily_category_totals() -> pd.DataFrame:
    records: list[dict[str, str | int | pd.Timestamp]] = []

    for json_file in sorted(DATA_DIR.glob("*.json")):
        try:
            date, trades = load_trade_payload(json_file)
        except FileNotFoundError:
            print(f"Warning: trade file missing or unavailable, skipping {json_file}")
            continue

        category_totals: Dict[str, int] = {}

        for trade in trades:
            ticker = trade_ticker(trade)
            category = classify_ticker(ticker)
            category_totals[category] = category_totals.get(category, 0) + trade_volume(
                trade
            )

        for category, total in category_totals.items():
            records.append({"date": date, "category": category, "volume": total})

    if not records:
        raise SystemExit(f"No trade files found in {DATA_DIR}")

    df = pd.DataFrame(records)
    df.sort_values("date", inplace=True)
    df = filter_complete_days(df)
    return df


def ensure_top_categories(pivot_df: pd.DataFrame, top_n: int = 10) -> list[str]:
    totals = pivot_df.sum(axis=0).sort_values(ascending=False)
    categories: list[str] = []

    for category in totals.index:
        if category == "Other":
            continue
        categories.append(category)
        if len(categories) == top_n - 1:
            break

    if "Other" in pivot_df.columns:
        categories.append("Other")

    if len(categories) < top_n:
        for category in totals.index:
            if category in categories:
                continue
            categories.append(category)
            if len(categories) == top_n:
                break

    return categories[:top_n]


def format_millions(x: float, pos: int) -> str:
    return f"{x / 1e6:,.1f}M"


def plot_top_categories(df: pd.DataFrame, top_n: int = 10, window: int = 7) -> Path:
    pivot = (
        df.pivot_table(index="date", columns="category", values="volume", fill_value=0)
        .sort_index()
        .asfreq("D", fill_value=0)
    )

    top_categories = ensure_top_categories(pivot, top_n=top_n)
    pivot = pivot[top_categories]

    rolling = pivot.rolling(window=window, min_periods=1).mean()

    plot_df = rolling.reset_index().melt(
        id_vars="date", var_name="Category", value_name="Volume"
    )

    fig, ax = plt.subplots(figsize=(15, 10))
    for category, group in plot_df.groupby("Category"):
        ax.plot(group["date"], group["Volume"], label=category, linewidth=2)

    ax.set_title("Top 10 Market Types – 7-Day Moving Average Volume Trends")
    ax.set_xlabel("Date")
    ax.set_ylabel("7-Day Moving Average Volume (Contracts)")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_millions))
    ax.grid(True, color="0.85", linewidth=0.8)

    ax.legend(title="", loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "top_10_market_types_7d_ma.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def main() -> None:
    df = load_daily_category_totals()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUTPUT_DIR / "daily_category_volume.csv"
    df.to_csv(csv_path, index=False, date_format="%Y-%m-%d")

    figure_path = plot_top_categories(df, top_n=10, window=7)

    print("Category totals saved to:", csv_path)
    print("Top 10 chart saved to:", figure_path)


if __name__ == "__main__":
    main()

