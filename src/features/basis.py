"""cross-currency basis (q1): btc/usd vs btc/usdt vs btc/usdc. we compute basis_usd_usdt = (close_usd - close_usdt)/close_usd in bps, same for usd-usdc and usdt-usdc. we use aligned files when present; fallback: build from clean coinbase-only data."""
from pathlib import Path

import pandas as pd

from src.utils import get_project_root, load_config


def _load_aligned(clean_base: Path, name: str) -> pd.DataFrame:
    p = clean_base / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def _close_col(df: pd.DataFrame) -> str:
    for x in ["coinbase", "binance", "kraken"]:
        c = f"close_{x}"
        if c in df.columns:
            return c
    for c in df.columns:
        if c.startswith("close_"):
            return c
    return "close"


def _build_from_clean_coinbase(clean_base: Path) -> pd.DataFrame:
    """build basis from clean coinbase single-exchange data when aligned files missing."""
    pairs = [("BTC-USD", "close_usd"), ("BTC-USDT", "close_usdt"), ("BTC-USDC", "close_usdc")]
    base = None
    for pair, col_out in pairs:
        p = clean_base / "coinbase" / f"{pair}_1m.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)[["time", "close"]].copy()
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.rename(columns={"close": col_out})
        if base is None:
            base = df
        else:
            base = base.merge(df, on="time", how="inner")
    return base if base is not None else pd.DataFrame()


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    clean_base = root / config["paths"]["clean"]
    derived_base = root / config["paths"]["derived"]
    derived_base.mkdir(parents=True, exist_ok=True)

    usd = _load_aligned(clean_base, "aligned_btc_usd.parquet")
    usdt = _load_aligned(clean_base, "aligned_btc_usdt.parquet")
    usdc = _load_aligned(clean_base, "aligned_btc_usdc.parquet")

    if not usd.empty and not usdt.empty and not usdc.empty:
        usd_close = _close_col(usd)
        usdt_close = _close_col(usdt)
        usdc_close = _close_col(usdc)
        base = usd[["time", usd_close]].rename(columns={usd_close: "close_usd"})
        base = base.merge(
            usdt[["time", usdt_close]].rename(columns={usdt_close: "close_usdt"}),
            on="time", how="inner",
        )
        base = base.merge(
            usdc[["time", usdc_close]].rename(columns={usdc_close: "close_usdc"}),
            on="time", how="inner",
        )
    else:
        base = _build_from_clean_coinbase(clean_base)

    if base.empty or "close_usd" not in base.columns:
        print("Basis: no data (need clean + align first).")
        return

    if "close_usdt" not in base.columns:
        base["close_usdt"] = pd.NA
    if "close_usdc" not in base.columns:
        base["close_usdc"] = pd.NA

    base["basis_usd_usdt_bps"] = (base["close_usd"] - base["close_usdt"]) / base["close_usd"] * 10_000
    base["basis_usd_usdc_bps"] = (base["close_usd"] - base["close_usdc"]) / base["close_usd"] * 10_000
    base["basis_usdt_usdc_bps"] = (base["close_usdt"] - base["close_usdc"]) / base["close_usdt"] * 10_000

    out_path = derived_base / "basis_1m.parquet"
    base.to_parquet(out_path, index=False)
    print(f"Saved {out_path} ({len(base)} rows)")


if __name__ == "__main__":
    run()
