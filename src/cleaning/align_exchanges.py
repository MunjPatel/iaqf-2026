"""cross-exchange alignment: we inner join on minute timestamp per pair-type. outputs aligned_btc_usd, aligned_btc_usdt, aligned_btc_usdc in data/clean/."""
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils import get_project_root, load_config


def load_clean(clean_base: Path, exchange: str, pair: str) -> Optional[pd.DataFrame]:
    p = clean_base / exchange / f"{pair}_1m.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def align_pair(
    clean_base: Path,
    out_path: Path,
    components,
    suffix_map,
) -> pd.DataFrame:
    """components: [(exchange, pair), ...]. suffix_map for column suffixes. we inner join on time with suffixed columns for close, volume, etc."""
    dfs = []
    for ex, pair in components:
        df = load_clean(clean_base, ex, pair)
        if df is None or df.empty:
            continue
        suf = suffix_map.get(ex, f"_{ex}")
        df = df[["time", "open", "high", "low", "close", "volume"]].copy()
        df = df.rename(columns={c: c + suf for c in ["open", "high", "low", "close", "volume"]})
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()
    out = dfs[0]
    for d in dfs[1:]:
        out = out.merge(d, on="time", how="inner")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)
    return out


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    clean_base = root / config["paths"]["clean"]
    suffix_map = {"coinbase": "_coinbase", "binance": "_binance", "kraken": "_kraken"}

    # align per pair-type
    alignments = [
        ("aligned_btc_usd.parquet", [("coinbase", "BTC-USD"), ("kraken", "XBTUSD")]),
        (
            "aligned_btc_usdt.parquet",
            [("coinbase", "BTC-USDT"), ("binance", "BTCUSDT"), ("kraken", "XBTUSDT")],
        ),
        (
            "aligned_btc_usdc.parquet",
            [("coinbase", "BTC-USDC"), ("binance", "BTCUSDC"), ("kraken", "XBTUSDC")],
        ),
    ]
    for out_name, components in alignments:
        out_path = clean_base / out_name
        print(f"Aligning {out_name} from {[c[1] for c in components]}...")
        df = align_pair(clean_base, out_path, components, suffix_map)
        if not df.empty:
            print(f"  -> {len(df)} rows")


if __name__ == "__main__":
    run()
