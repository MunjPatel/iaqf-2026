"""
§2.2 Step 4: log_return = ln(close_t / close_{t-1}); realized_vol_5m = std(log_return)*sqrt(5) on rolling 5m.
"""
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

    # Use aligned single-pair or multi-exchange; for returns we can use one close per pair
    basis_path = derived_base / "basis_1m.parquet"
    if not basis_path.exists():
        print("Returns: run features.basis first to create basis_1m.parquet with close_*.")
        return
    df = pd.read_parquet(basis_path)
    df["time"] = pd.to_datetime(df["time"], utc=True)

    for col in ["close_usd", "close_usdt", "close_usdc"]:
        if col not in df.columns:
            continue
        name = col.replace("close_", "")
        df[f"log_return_{name}"] = np.log(df[col] / df[col].shift(1))
        # Rolling 5-min realized vol (std of log returns * sqrt(5))
        df[f"realized_vol_5m_{name}"] = (
            df[f"log_return_{name}"].rolling(5, min_periods=2).std() * np.sqrt(5)
        )

    out_path = derived_base / "returns_1m.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Saved {out_path} ({len(df)} rows)")


if __name__ == "__main__":
    run()
