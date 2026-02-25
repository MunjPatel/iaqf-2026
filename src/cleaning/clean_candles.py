"""
§2.2 Step 2: Clean raw candles — grid alignment, forward-fill ≤5 min gaps, validate, save to data/clean/.
"""
from pathlib import Path

import pandas as pd
import numpy as np

from src.utils import get_project_root, load_config, parse_window


def build_minute_grid(start_utc, end_utc) -> pd.DatetimeIndex:
    """Full 1-minute grid from start to end (inclusive of last minute before end). 21 days = 30,240 candles."""
    grid = pd.date_range(start=start_utc, end=end_utc, freq="1min", inclusive="left")
    return grid


def clean_one(
    raw_path: Path,
    out_path: Path,
    grid: pd.DatetimeIndex,
    max_fill: int,
) -> pd.DataFrame:
    """
    Load raw parquet, left-join to grid, forward-fill gaps ≤ max_fill minutes, validate, save.
    """
    df = pd.read_parquet(raw_path)
    if "open_time" in df.columns:
        df = df.rename(columns={"open_time": "time"})
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    else:
        df["time"] = df["time"].dt.tz_convert("UTC")
    df = df.sort_values("time").drop_duplicates(subset=["time"], keep="first")

    grid_df = pd.DataFrame({"time": grid})
    merged = grid_df.merge(df, on="time", how="left")

    # Ensure we have standard OHLCV columns (Kraken has vwap, count — keep time, o, h, l, c, volume)
    for c in ["open", "high", "low", "close", "volume"]:
        if c not in merged.columns:
            merged[c] = np.nan

    merged = merged[["time", "open", "high", "low", "close", "volume"]].copy()
    merged["time"] = pd.to_datetime(merged["time"], utc=True).astype("datetime64[ns, UTC]")
    for col in ["open", "high", "low", "close", "volume"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    # Consecutive missing: forward-fill close with limit = max_fill (only fill up to 5 in a row)
    merged["close"] = merged["close"].ffill(limit=max_fill).bfill(limit=max_fill)
    # Rows that got filled (had NaN open but now have close): set volume=0, ohlc=close
    filled_mask = merged["open"].isna() & merged["close"].notna()
    merged.loc[filled_mask, "open"] = merged.loc[filled_mask, "close"]
    merged.loc[filled_mask, "high"] = merged.loc[filled_mask, "close"]
    merged.loc[filled_mask, "low"] = merged.loc[filled_mask, "close"]
    merged.loc[filled_mask, "volume"] = 0.0

    # Validate
    valid = merged["close"].notna()
    if valid.any():
        assert (merged.loc[valid, "close"] >= 0).all(), "Negative close"
        assert ((merged["volume"] >= 0) | merged["volume"].isna()).all(), "Negative volume"
        assert (merged.loc[valid, "low"] <= merged.loc[valid, "close"]).all()
        assert (merged.loc[valid, "high"] >= merged.loc[valid, "close"]).all()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path, index=False)
    return merged


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    raw_base = root / config["paths"]["raw"]
    clean_base = root / config["paths"]["clean"]
    start_utc, end_utc = parse_window(config)
    grid = build_minute_grid(start_utc, end_utc)
    max_fill = config["cleaning"]["max_consecutive_missing_forward_fill"]

    layouts = [
        ("coinbase", ["BTC-USD", "BTC-USDT", "BTC-USDC"]),
        ("binance", ["BTCUSDT", "BTCUSDC"]),
        ("kraken", ["XBTUSD", "XBTUSDT", "XBTUSDC"]),
    ]
    for exchange, pairs in layouts:
        for pair in pairs:
            raw_path = raw_base / exchange / f"{pair}_1m.parquet"
            if not raw_path.exists():
                print(f"Skip (no raw): {raw_path}")
                continue
            out_path = clean_base / exchange / f"{pair}_1m.parquet"
            print(f"Cleaning {exchange}/{pair} -> {out_path}")
            clean_one(raw_path, out_path, grid, max_fill)


if __name__ == "__main__":
    run()
