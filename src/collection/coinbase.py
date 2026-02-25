"""
Coinbase Exchange (Pro REST API) candle collector.
§2.1: GET .../products/{pair}/candles — start, end, granularity=60.
Fields: [timestamp, low, high, open, close, volume]. Max 300 candles/request (5h of 1m).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

from src.utils import get_project_root, load_config, parse_window


def fetch_candles(
    session: requests.Session,
    base_url: str,
    pair: str,
    start_utc,
    end_utc,
    granularity: int = 60,
    max_candles: int = 300,
    sleep_s: float = 0.2,
    max_retries: int = 5,
):
    """Fetch 1m candles in chunks. Returns list of raw rows [timestamp, low, high, open, close, volume]."""
    url = f"{base_url}/products/{pair}/candles"
    all_rows = []
    start = start_utc

    while start < end_utc:
        chunk_end_ts = min(
            start.timestamp() + (max_candles - 1) * 60,
            end_utc.timestamp() - 1,
        )
        chunk_end = pd.Timestamp(chunk_end_ts, unit="s", tz="UTC")

        params = {
            "start": start.isoformat(),
            "end": chunk_end.isoformat(),
            "granularity": granularity,
        }

        for attempt in range(max_retries):
            r = session.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                n = len(data)
                print(f"  {pair}: chunk {start} -> {chunk_end} | {n} candles")
                all_rows.extend(data)
                break
            if r.status_code == 429:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
        else:
            raise RuntimeError(f"Max retries exceeded for {pair} at {start}")

        if not data:
            break
        start = chunk_end + pd.Timedelta(minutes=1)
        time.sleep(sleep_s)

    return all_rows


def raw_to_dataframe(rows: list) -> pd.DataFrame:
    """Parse Coinbase raw rows to DataFrame. Columns: time, low, high, open, close, volume."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        rows,
        columns=["time", "low", "high", "open", "close", "volume"],
    )
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.sort_values("time", ignore_index=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    raw_dir = root / config["paths"]["raw"] / "coinbase"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_utc, end_utc = parse_window(config)
    cb = config["coinbase"]
    base_url = cb["base_url"]
    pairs = cb["pairs"]
    max_candles = cb["max_candles_per_request"]
    sleep_s = cb["rate_limit_sleep_seconds"]
    granularity = 60  # 1m

    session = requests.Session()

    for pair in pairs:
        print(f"Fetching Coinbase {pair}...")
        rows = fetch_candles(
            session,
            base_url,
            pair,
            start_utc,
            end_utc,
            granularity=granularity,
            max_candles=max_candles,
            sleep_s=sleep_s,
        )
        if not rows:
            print(f"  {pair}: No data.")
            continue

        # Save raw JSON first (§2.2 Step 1)
        raw_json_path = raw_dir / f"{pair}_1m_raw.json"
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=None)
        print(f"  Saved raw JSON: {raw_json_path} ({len(rows)} candles)")

        df = raw_to_dataframe(rows)
        parquet_path = raw_dir / f"{pair}_1m.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved parquet: {parquet_path} ({len(df)} rows)")


if __name__ == "__main__":
    run()
