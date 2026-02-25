"""we compute hl_spread_proxy = (high-low)/((high+low)/2) and volume_usd = volume*close. parkinson, amihud, dollar volume in analysis."""
from pathlib import Path

import pandas as pd
import numpy as np

from src.utils import get_project_root, load_config


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    clean_base = root / config["paths"]["clean"]
    derived_base = root / config["paths"]["derived"]
    derived_base.mkdir(parents=True, exist_ok=True)

    layouts = [
        ("coinbase", ["BTC-USD", "BTC-USDT", "BTC-USDC"]),
        ("binance", ["BTCUSDT", "BTCUSDC"]),
        ("kraken", ["XBTUSD", "XBTUSDT", "XBTUSDC"]),
    ]
    all_dfs = []
    for exchange, pairs in layouts:
        for pair in pairs:
            p = clean_base / exchange / f"{pair}_1m.parquet"
            if not p.exists():
                continue
            df = pd.read_parquet(p)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            mid = (df["high"] + df["low"]) / 2
            df["hl_spread_proxy"] = (df["high"] - df["low"]) / mid.replace(0, np.nan)
            df["volume_usd"] = df["volume"] * df["close"]
            df["exchange"] = exchange
            df["pair"] = pair
            all_dfs.append(df)

    if not all_dfs:
        print("Liquidity: no clean candle files found.")
        return
    out = pd.concat(all_dfs, ignore_index=True)
    out_path = derived_base / "liquidity_1m.parquet"
    out.to_parquet(out_path, index=False)
    print(f"Saved {out_path} ({len(out)} rows)")


if __name__ == "__main__":
    run()
