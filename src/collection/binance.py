"""
Binance REST API klines collector.
§2.1: GET api.binance.com/api/v3/klines — symbol, interval=1m, startTime, endTime, limit=1000.
Pairs: BTCUSDT, BTCUSDC (no BTC/USD). Use open_time as canonical timestamp (§2.3).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

from src.utils import get_project_root, load_config, parse_window

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_vol", "trades",
    "taker_base_vol", "taker_quote_vol", "ignore",
]


def fetch_klines(
    session: requests.Session,
    base_url: str,
    symbol: str,
    start_ts: int,
    end_ts: int,
    interval: str = "1m",
    limit: int = 1000,
    sleep_s: float = 0.35,
    max_retries: int = 5,
):
    """Fetch 1m klines in chunks. start_ts/end_ts in seconds (API uses ms)."""
    url = f"{base_url}/api/v3/klines"
    all_rows = []
    req_start = start_ts * 1000
    end_ms = end_ts * 1000

    while req_start < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": req_start,
            "endTime": end_ms,
            "limit": limit,
        }

        for attempt in range(max_retries):
            r = session.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                n = len(data)
                if n:
                    last_close_ms = data[-1][6]
                    t_start = pd.Timestamp(req_start, unit="ms", tz="UTC")
                    t_end = pd.Timestamp(last_close_ms, unit="ms", tz="UTC")
                    print(f"  {symbol}: chunk {t_start} -> {t_end} | {n} candles")
                all_rows.extend(data)
                break
            if r.status_code == 429:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
        else:
            raise RuntimeError(f"Max retries exceeded for {symbol} at {req_start}")

        if not data:
            break
        last_close_time_ms = data[-1][6]
        if last_close_time_ms >= end_ms:
            break
        req_start = last_close_time_ms + 1
        time.sleep(sleep_s)

    return all_rows


def raw_to_dataframe(rows: list) -> pd.DataFrame:
    """Parse Binance klines to DataFrame. Canonical time = open_time (§2.3)."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=COLUMNS)

    numeric_cols = [
        "open", "high", "low", "close", "volume",
        "quote_asset_vol", "taker_base_vol", "taker_quote_vol",
    ]
    df[numeric_cols] = df[numeric_cols].astype(float)
    df["trades"] = df["trades"].astype(int)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.rename(columns={"open_time": "time"})
    df = df.sort_values("time", ignore_index=True)
    return df


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    raw_dir = root / config["paths"]["raw"] / "binance"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_utc, end_utc = parse_window(config)
    start_ts = int(start_utc.timestamp())
    end_ts = int(end_utc.timestamp())

    bn = config["binance"]
    base_url = bn["base_url"]
    pairs = bn["pairs"]
    limit = bn["max_candles_per_request"]
    sleep_s = bn["rate_limit_sleep_seconds"]

    session = requests.Session()

    for symbol in pairs:
        print(f"Fetching Binance {symbol}...")
        rows = fetch_klines(
            session,
            base_url,
            symbol,
            start_ts,
            end_ts,
            interval="1m",
            limit=limit,
            sleep_s=sleep_s,
        )
        if not rows:
            print(f"  {symbol}: No data.")
            continue

        raw_json_path = raw_dir / f"{symbol}_1m_raw.json"
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=None)
        print(f"  Saved raw JSON: {raw_json_path} ({len(rows)} candles)")

        df = raw_to_dataframe(rows)
        parquet_path = raw_dir / f"{symbol}_1m.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved parquet: {parquet_path} ({len(df)} rows)")


if __name__ == "__main__":
    run()
