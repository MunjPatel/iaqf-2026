"""
Export key figures as PNG for the paper. Run from project root with PYTHONPATH set.
Requires: pip install kaleido (or plotly[ Kaleido]).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils import get_project_root, load_config

# Reuse styling from plots
COLORS = {"usd_usdt": "#0173B2", "usd_usdc": "#DE8F05", "usdt_usdc": "#029E73"}
REGIME_COLORS = {"pre": "rgba(0,150,80,0.12)", "crisis": "rgba(200,50,50,0.15)", "post": "rgba(70,100,180,0.10)"}


def _to_plotly_ts(d):
    return int(pd.Timestamp(d).value / 1e6)


def _regime_shapes():
    return [
        dict(x0=_to_plotly_ts("2023-03-01"), x1=_to_plotly_ts("2023-03-10"), fillcolor=REGIME_COLORS["pre"], line={"width": 0}),
        dict(x0=_to_plotly_ts("2023-03-10"), x1=_to_plotly_ts("2023-03-14"), fillcolor=REGIME_COLORS["crisis"], line={"width": 0}),
        dict(x0=_to_plotly_ts("2023-03-14"), x1=_to_plotly_ts("2023-03-22"), fillcolor=REGIME_COLORS["post"], line={"width": 0}),
    ]


def export_all():
    config = load_config()
    root = get_project_root()
    derived = root / config["paths"]["derived"]
    results = root / "results"
    out_dir = root / "paper" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Basis time series
    path = derived / "basis_1m.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.sort_values("time")
        fig = go.Figure()
        for col, label, color in [
            ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"]),
            ("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]),
            ("basis_usdt_usdc_bps", "USDT vs USDC", COLORS["usdt_usdc"]),
        ]:
            if col in df.columns and df[col].notna().any():
                fig.add_trace(go.Scatter(x=df["time"], y=df[col], name=label, mode="lines", line={"width": 2, "color": color}))
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(0,0,0,0.4)")
        for s in _regime_shapes():
            fig.add_vrect(**s)
        fig.update_layout(
            title="Cross-Currency Basis (bps), March 2023",
            xaxis_title="Time (UTC)", yaxis_title="Basis (bps)",
            template="plotly_white", height=380, font=dict(size=11),
            legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
        )
        fig.write_image(str(out_dir / "fig1_basis_timeseries.png"), scale=2)
        print("Wrote fig1_basis_timeseries.png")

    # 2. Stablecoin discount
    if path.exists():
        df = pd.read_parquet(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        if "close_usd" in df.columns and "close_usdc" in df.columns:
            df["usdc_discount_bps"] = (1 - df["close_usd"] / df["close_usdc"]) * 10_000
            if "close_usdt" in df.columns:
                df["usdt_discount_bps"] = (1 - df["close_usd"] / df["close_usdt"]) * 10_000
            df = df.sort_values("time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["usdc_discount_bps"], name="USDC discount (bps)", line=dict(width=2, color=COLORS["usd_usdc"])))
            if "usdt_discount_bps" in df.columns:
                fig.add_trace(go.Scatter(x=df["time"], y=df["usdt_discount_bps"], name="USDT discount (bps)", line=dict(width=2, color=COLORS["usd_usdt"])))
            for s in _regime_shapes():
                fig.add_vrect(**s)
            fig.add_hline(y=0, line_dash="dot", line_color="black")
            fig.update_layout(title="Stablecoin Implied Discount from Peg (bps)", xaxis_title="Time (UTC)", yaxis_title="Discount (bps)", template="plotly_white", height=380, font=dict(size=11))
            fig.write_image(str(out_dir / "fig2_stablecoin_discount.png"), scale=2)
            print("Wrote fig2_stablecoin_discount.png")

    # 3. Basis by regime (bar)
    csv_path = results / "basis_summary_by_regime.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        color_map = {"USD-USDT": COLORS["usd_usdt"], "USD-USDC": COLORS["usd_usdc"], "USDT-USDC": COLORS["usdt_usdc"]}
        fig = px.bar(df, x="regime", y="mean_bps", color="basis", barmode="group", text_auto=".2f",
                     labels={"mean_bps": "Mean basis (bps)", "regime": "Regime"}, color_discrete_map=color_map)
        fig.update_layout(template="plotly_white", height=360, font=dict(size=11), title="Mean Basis (bps) by Regime")
        fig.write_image(str(out_dir / "fig3_basis_by_regime.png"), scale=2)
        print("Wrote fig3_basis_by_regime.png")

    # 4. Liquidity (spread and volume)
    liq_path = derived / "liquidity_1m.parquet"
    if liq_path.exists():
        df = pd.read_parquet(liq_path)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df["hl_spread_bps"] = df["hl_spread_proxy"] * 10_000
        df["time1h"] = df["time"].dt.floor("1h")
        r = df.groupby(["exchange", "pair", "time1h"]).agg(
            hl_spread_bps=("hl_spread_proxy", lambda x: (x.dropna() * 10_000).mean()),
            volume_usd=("volume_usd", "sum"),
        ).reset_index()
        r.rename(columns={"time1h": "time"}, inplace=True)
        fig = make_subplots(rows=2, cols=1, subplot_titles=("High-Low spread (bps, 1h avg)", "Volume USD (1h sum)"), vertical_spacing=0.15, row_heights=[0.5, 0.5])
        for (ex, pair), g in r.groupby(["exchange", "pair"]):
            fig.add_trace(go.Scatter(x=g["time"], y=g["hl_spread_bps"], name=f"{ex} {pair}", line=dict(width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=g["time"], y=g["volume_usd"], name=f"{ex} {pair}", line=dict(width=1.2), showlegend=False), row=2, col=1)
        for s in _regime_shapes():
            fig.add_vrect(**s, row=1, col=1)
            fig.add_vrect(**s, row=2, col=1)
        fig.update_layout(template="plotly_white", height=420, font=dict(size=11), title_text="Liquidity: Spread and Volume by Exchange/Pair")
        fig.update_yaxes(title_text="Spread (bps)", row=1, col=1)
        fig.update_yaxes(title_text="Volume USD", row=2, col=1)
        fig.write_image(str(out_dir / "fig4_liquidity.png"), scale=2)
        print("Wrote fig4_liquidity.png")

    print(f"Figures saved to {out_dir}")


if __name__ == "__main__":
    try:
        export_all()
    except Exception as e:
        print("Export failed (install kaleido: pip install kaleido):", e)
