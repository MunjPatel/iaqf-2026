"""kraken rest api ohlc collector. we fetch 1m ohlc in chunks (720/request). kraken uses xbt vs btc tickers; rate limit 1 req/s."""
import json
import time

import pandas as pd
import requests

from src.utils import get_project_root, load_config, parse_window

# kraken returns pair key dynamically (e.g. xxbtzusd). we take the first key in result
OHLC_COLUMNS = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]


def fetch_ohlc(
    session: requests.Session,
    base_url: str,
    pair: str,
    start_ts: int,
    end_ts: int,
    interval: int = 1,
    sleep_s: float = 1.0,
    max_retries: int = 5,
):
    """fetch 1m ohlc. start_ts/end_ts in seconds. returns list of [time, o, h, l, c, vwap, vol, count]."""
    url = f"{base_url}/0/public/OHLC"
    all_rows = []
    since = start_ts

    while since < end_ts:
        params = {
            "pair": pair,
            "interval": interval,
            "since": since,
        }

        for attempt in range(max_retries):
            r = session.get(url, params=params)
            if r.status_code == 200:
                out = r.json()
                if out.get("error") and out["error"]:
                    # e.g. unknown pair — try alt pair name
                    raise RuntimeError(f"Kraken API error: {out['error']}")
                result = out.get("result") or {}
                # result has one key (pair id, e.g. xxbtzusd or xbtusd)
                keys = [k for k in result if k != "last"]
                if not keys:
                    break
                pair_key = keys[0]
                data = result[pair_key]
                n = len(data)
                if n:
                    t_start = pd.Timestamp(data[0][0], unit="s", tz="UTC")
                    t_end = pd.Timestamp(data[-1][0], unit="s", tz="UTC")
                    print(f"  {pair}: chunk {t_start} -> {t_end} | {n} candles")
                all_rows.extend(data)
                if "last" in result:
                    since = result["last"]
                else:
                    since = end_ts
                break
            if r.status_code == 429:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
        else:
            raise RuntimeError(f"Max retries exceeded for {pair} at since={since}")

        if not data:
            break
        if since >= end_ts:
            break
        time.sleep(sleep_s)

    return all_rows


def raw_to_dataframe(rows: list) -> pd.DataFrame:
    """parse kraken ohlc to dataframe."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=OHLC_COLUMNS)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for col in ["open", "high", "low", "close", "volume", "vwap"]:
        df[col] = df[col].astype(float)
    df["count"] = df["count"].astype(int)
    df = df.sort_values("time", ignore_index=True)
    return df


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    raw_dir = root / config["paths"]["raw"] / "kraken"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_utc, end_utc = parse_window(config)
    start_ts = int(start_utc.timestamp())
    end_ts = int(end_utc.timestamp())

    kr = config["kraken"]
    base_url = kr["base_url"]
    pairs = kr["pairs"]
    sleep_s = kr["rate_limit_sleep_seconds"]

    session = requests.Session()

    for pair in pairs:
        print(f"Fetching Kraken {pair}...")
        rows = fetch_ohlc(
            session,
            base_url,
            pair,
            start_ts,
            end_ts,
            interval=1,
            sleep_s=sleep_s,
        )
        if not rows:
            print(f"  {pair}: No data.")
            continue

        df = raw_to_dataframe(rows)
        t_min, t_max = df["time"].min(), df["time"].max()
        if t_min > end_utc or t_max < start_utc:
            print(f"  WARNING: Kraken returned {t_min} to {t_max}, not requested {start_utc} to {end_utc}.")
            print("  Kraken public OHLC only returns ~720 most recent candles (no historical).")

        raw_json_path = raw_dir / f"{pair}_1m_raw.json"
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=None)
        print(f"  Saved raw JSON: {raw_json_path} ({len(rows)} candles)")
        parquet_path = raw_dir / f"{pair}_1m.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved parquet: {parquet_path} ({len(df)} rows)")


if __name__ == "__main__":
    run()
