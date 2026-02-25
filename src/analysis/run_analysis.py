"""
Run all analyses for IAQF 2026 (4 questions) and save summary results to data/derived/ and results/.
Problem: Cross-currency dynamics, stablecoin regulation, March 1-21 2023.
"""
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np

from src.utils import get_project_root, load_config, parse_window, SVB_ANNOUNCE_UTC, USDC_DEPEG_TROUGH_UTC


def _regime_mask(df: pd.DataFrame) -> pd.Series:
    """Pre-SVB (Mar 1-9), SVB crisis (Mar 10-13), Post-SVB (Mar 14-21)."""
    t = pd.to_datetime(df["time"], utc=True)
    pre = t < datetime(2023, 3, 10, tzinfo=timezone.utc)
    crisis = (t >= datetime(2023, 3, 10, tzinfo=timezone.utc)) & (t < datetime(2023, 3, 14, tzinfo=timezone.utc))
    post = t >= datetime(2023, 3, 14, tzinfo=timezone.utc)
    return pre, crisis, post


def run_basis_analysis(derived_base: Path, results_dir: Path) -> pd.DataFrame:
    """Q1: Cross-currency basis — stats by regime, transaction-cost note."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    pre, crisis, post = _regime_mask(df)

    rows = []
    for name, col in [("USD-USDT", "basis_usd_usdt_bps"), ("USD-USDC", "basis_usd_usdc_bps"), ("USDT-USDC", "basis_usdt_usdc_bps")]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if s.empty:
            continue
        for regime, mask in [("Pre-SVB (Mar 1-9)", pre), ("SVB crisis (Mar 10-13)", crisis), ("Post-SVB (Mar 14-21)", post)]:
            r = s.loc[mask]
            if r.empty:
                continue
            rows.append({
                "basis": name,
                "regime": regime,
                "mean_bps": round(r.mean(), 4),
                "std_bps": round(r.std(), 4),
                "median_bps": round(r.median(), 4),
                "min_bps": round(r.min(), 4),
                "max_bps": round(r.max(), 4),
                "count": len(r),
            })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out.to_csv(results_dir / "basis_summary_by_regime.csv", index=False)
    return out


def run_stablecoin_analysis(derived_base: Path, results_dir: Path) -> pd.DataFrame:
    """Q2: Stablecoin premium/discount — implied USDC/USDT vs USD from basis."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    if "close_usd" not in df.columns or "close_usdc" not in df.columns:
        return pd.DataFrame()
    # Implied USDC/USD = close_BTCUSD / close_BTCUSDC (deviation from 1 = discount)
    df["usdc_usd_implied"] = df["close_usd"] / df["close_usdc"]
    df["usdc_discount_bps"] = (1 - df["usdc_usd_implied"]) * 10_000
    if "close_usdt" in df.columns:
        df["usdt_usd_implied"] = df["close_usd"] / df["close_usdt"]
        df["usdt_discount_bps"] = (1 - df["usdt_usd_implied"]) * 10_000
    pre, crisis, post = _regime_mask(df)
    rows = []
    for col in ["usdc_discount_bps", "usdt_discount_bps"]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if s.empty:
            continue
        for regime, mask in [("Pre-SVB", pre), ("SVB crisis", crisis), ("Post-SVB", post)]:
            r = s.loc[mask]
            if r.empty:
                continue
            rows.append({
                "metric": col.replace("_bps", ""),
                "regime": regime,
                "mean_bps": round(r.mean(), 2),
                "std_bps": round(r.std(), 2),
                "median_bps": round(r.median(), 2),
                "count": len(r),
            })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out.to_csv(results_dir / "stablecoin_discount_by_regime.csv", index=False)
    return out


def run_liquidity_analysis(derived_base: Path, results_dir: Path) -> pd.DataFrame:
    """Q3: Liquidity & fragmentation — spread proxy, volume by quote currency and exchange."""
    path = derived_base / "liquidity_1m.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    # Quote currency from pair name
    def quote(p):
        p = str(p).upper()
        if "USDT" in p:
            return "USDT"
        if "USDC" in p:
            return "USDC"
        if "USD" in p or "XBT" in p:
            return "USD"
        return "other"
    df["quote_ccy"] = df["pair"].map(quote)
    pre, crisis, post = _regime_mask(df)
    agg = df.groupby(["exchange", "quote_ccy", "pair"]).agg(
        hl_spread_bps=("hl_spread_proxy", lambda x: (x.dropna() * 10_000).mean()),
        volume_usd_sum=("volume_usd", "sum"),
        count=("time", "count"),
    ).reset_index()
    agg["hl_spread_bps"] = agg["hl_spread_bps"].round(4)
    agg.to_csv(results_dir / "liquidity_by_exchange_quote.csv", index=False)
    by_regime = []
    for regime_name, mask in [("Pre-SVB", pre), ("SVB crisis", crisis), ("Post-SVB", post)]:
        sub = df.loc[mask]
        if sub.empty:
            continue
        r = sub.groupby(["exchange", "quote_ccy"]).agg(
            mean_hl_spread_bps=("hl_spread_proxy", lambda x: (x.dropna() * 10_000).mean()),
            total_volume_usd=("volume_usd", "sum"),
        ).reset_index()
        r["regime"] = regime_name
        by_regime.append(r)
    if by_regime:
        pd.concat(by_regime, ignore_index=True).to_csv(results_dir / "liquidity_by_regime.csv", index=False)
    return agg


def run_regulatory_summary(results_dir: Path) -> str:
    """Q4: Regulatory overlay — map findings to GENIUS Act / policy (text)."""
    text = """
## Regulatory Overlay (IAQF 2026 Q4)

### Empirical findings and policy implications

1. **Cross-currency basis persistence**  
   If we observe persistent basis between BTC/USD and BTC/USDT after transaction costs, it suggests market fragmentation and differing counterparty/regulatory risk. The GENIUS Act’s reserve transparency and oversight can reduce information asymmetry and support faster convergence of cross-currency prices.

2. **Stablecoin stress (USDC de-peg)**  
   The March 2023 USDC de-peg (SVB) shows how reserve and redemption uncertainty amplifies discount in stablecoin-quoted markets. Mandatory 1:1 reserve backing and clear redemption rights under the GENIUS Act would be expected to improve peg resilience and shorten stress periods.

3. **Liquidity and fragmentation**  
   Differences in spread and volume across USD vs stablecoin-quoted pairs inform execution and hedging choices. Regulatory clarity may concentrate volume on compliant venues (reducing fragmentation) but also raises concentration risk—relevant for market structure policy.

4. **Implications for trading and policy**  
   For institutional adoption (e.g. Visa USDC settlement), reliable peg and tight cross-currency basis are essential. Our empirical results on basis and stablecoin discount during the SVB window quantify the type of risk that regulation aims to mitigate.
"""
    out = results_dir / "regulatory_overlay.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text.strip())
    return text


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    derived_base = root / config["paths"]["derived"]
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("Running basis analysis (Q1)...")
    run_basis_analysis(derived_base, results_dir)
    print("Running stablecoin analysis (Q2)...")
    run_stablecoin_analysis(derived_base, results_dir)
    print("Running liquidity analysis (Q3)...")
    run_liquidity_analysis(derived_base, results_dir)
    print("Writing regulatory overlay (Q4)...")
    run_regulatory_summary(results_dir)
    print(f"Results saved under {results_dir}")


if __name__ == "__main__":
    run()
