"""interactive plotly figures: basis, stablecoin discount, liquidity, regulatory. we save html to results/ for dashboard embedding and add news-event annotations plus standout plots."""
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils import get_project_root, load_config, SVB_ANNOUNCE_UTC, USDC_DEPEG_TROUGH_UTC

# colorblind-friendly palette, same across all plots
COLORS = {"usd_usdt": "#0173B2", "usd_usdc": "#DE8F05", "usdt_usdc": "#029E73"}
REGIME_COLORS = {"pre": "rgba(0,150,80,0.12)", "crisis": "rgba(200,50,50,0.15)", "post": "rgba(70,100,180,0.10)"}


def _to_plotly_ts(d):
    """convert datetime to plotly x-axis value (ms since epoch)."""
    return int(pd.Timestamp(d).value / 1e6)


def _regime_vertical_shapes():
    """vertical shaded regions for pre-svb, svb crisis, post-svb (numeric x for plotly)."""
    return [
        dict(x0=_to_plotly_ts("2023-03-01"), x1=_to_plotly_ts("2023-03-10"), fillcolor=REGIME_COLORS["pre"], line={"width": 0}),
        dict(x0=_to_plotly_ts("2023-03-10"), x1=_to_plotly_ts("2023-03-14"), fillcolor=REGIME_COLORS["crisis"], line={"width": 0}),
        dict(x0=_to_plotly_ts("2023-03-14"), x1=_to_plotly_ts("2023-03-22"), fillcolor=REGIME_COLORS["post"], line={"width": 0}),
    ]


def _load_news_events(verify_links=False):
    """load events. for dashboard we use verify_links=True so only working urls show."""
    try:
        from src.visualization.news_events import load_news_events
        return load_news_events(verify_links=verify_links)
    except Exception:
        return []


def plot_basis_timeseries(derived_base: Path, results_dir: Path) -> str:
    """q1: interactive basis with zero line, regime bands, news-event vlines."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time")

    fig = go.Figure()
    series = [
        ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"]),
        ("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]),
        ("basis_usdt_usdc_bps", "USDT vs USDC", COLORS["usdt_usdc"]),
    ]
    for col, label, color in series:
        if col not in df.columns or df[col].dropna().empty:
            continue
        fig.add_trace(go.Scatter(
            x=df["time"], y=df[col], name=label, mode="lines",
            line={"width": 2.2, "color": color},
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(0,0,0,0.4)", line_width=1)
    for s in _regime_vertical_shapes():
        fig.add_vrect(**s)
    for ts, name, url in _load_news_events():
        fig.add_vline(x=_to_plotly_ts(ts), line_dash="dash", line_color="rgba(100,100,100,0.8)", line_width=1.2)
    fig.update_layout(
        title=dict(text="Q1: Cross-Currency Basis", font=dict(size=16)),
        xaxis_title="Time (UTC)",
        yaxis_title="Basis (bps)",
        hovermode="x unified",
        template="plotly_white",
        height=480,
        font=dict(size=12),
        margin=dict(t=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.06)"),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.06)", zeroline=True, zerolinewidth=1),
    )
    out = results_dir / "plot_basis_timeseries.html"
    fig.write_html(str(out))
    return str(out)


def plot_stablecoin_discount(derived_base: Path, results_dir: Path) -> str:
    """q2: usdc/usdt implied discount from peg (1.00) over time."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    if "close_usd" not in df.columns or "close_usdc" not in df.columns:
        return ""
    df["usdc_discount_bps"] = (1 - df["close_usd"] / df["close_usdc"]) * 10_000
    if "close_usdt" in df.columns:
        df["usdt_discount_bps"] = (1 - df["close_usd"] / df["close_usdt"]) * 10_000
    df = df.sort_values("time")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time"], y=df["usdc_discount_bps"], name="USDC discount (bps)", mode="lines", line={"width": 1.5}))
    if "usdt_discount_bps" in df.columns:
        fig.add_trace(go.Scatter(x=df["time"], y=df["usdt_discount_bps"], name="USDT discount (bps)", mode="lines", line={"width": 1.5}))
    for x, name in [(SVB_ANNOUNCE_UTC, "SVB"), (USDC_DEPEG_TROUGH_UTC, "USDC trough")]:
        fig.add_vline(x=_to_plotly_ts(x), line_dash="dash", line_color="gray", annotation_text=name)
    for s in _regime_vertical_shapes():
        fig.add_vrect(**s)
    fig.add_hline(y=0, line_dash="dot", line_color="black")
    fig.update_layout(
        title="Stablecoin Implied Discount from Peg (1.00), March 2023",
        xaxis_title="Time (UTC)",
        yaxis_title="Discount (bps)",
        hovermode="x unified",
        template="plotly_white",
        height=420,
    )
    out = results_dir / "plot_stablecoin_discount.html"
    fig.write_html(str(out))
    return str(out)


def plot_liquidity_by_quote(derived_base: Path, results_dir: Path) -> str:
    """q3: liquidity — hl spread (bps) and volume by exchange and quote currency."""
    path = derived_base / "liquidity_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["hl_spread_bps"] = df["hl_spread_proxy"] * 10_000
    df["time1h"] = pd.to_datetime(df["time"], utc=True).dt.floor("1h")
    r = df.groupby(["exchange", "pair", "time1h"]).agg(
        hl_spread_bps=("hl_spread_proxy", lambda x: (x.dropna() * 10_000).mean()),
        volume_usd=("volume_usd", "sum"),
    ).reset_index()
    r.rename(columns={"time1h": "time"}, inplace=True)

    fig = make_subplots(rows=2, cols=1, subplot_titles=("High-Low spread (bps, 1h avg)", "Volume USD (1h sum)"), vertical_spacing=0.12, row_heights=[0.5, 0.5])
    for (ex, pair), g in r.groupby(["exchange", "pair"]):
        fig.add_trace(go.Scatter(x=g["time"], y=g["hl_spread_bps"], name=f"{ex} {pair}", mode="lines", line={"width": 1.2}), row=1, col=1)
        fig.add_trace(go.Scatter(x=g["time"], y=g["volume_usd"], name=f"{ex} {pair}", mode="lines", line={"width": 1.2}, showlegend=False), row=2, col=1)
    for s in _regime_vertical_shapes():
        fig.add_vrect(**s, row=1, col=1)
        fig.add_vrect(**s, row=2, col=1)
    fig.update_layout(template="plotly_white", height=560, hovermode="x unified", title_text="Liquidity: Spread and Volume by Exchange/Pair (March 2023)")
    fig.update_yaxes(title_text="Spread (bps)", row=1, col=1)
    fig.update_yaxes(title_text="Volume USD", row=2, col=1)
    out = results_dir / "plot_liquidity.html"
    fig.write_html(str(out))
    return str(out)


def plot_basis_by_regime(results_dir: Path) -> str:
    """bar chart: mean basis by regime (from basis_summary_by_regime.csv)."""
    path = results_dir / "basis_summary_by_regime.csv"
    if not path.exists():
        return ""
    df = pd.read_csv(path)
    color_map = {"USD-USDT": COLORS["usd_usdt"], "USD-USDC": COLORS["usd_usdc"], "USDT-USDC": COLORS["usdt_usdc"]}
    fig = px.bar(df, x="regime", y="mean_bps", color="basis", barmode="group", text_auto=".2f",
                 title="Mean Cross-Currency Basis (bps) by Regime",
                 labels={"mean_bps": "Mean basis (bps)", "regime": "Regime"},
                 color_discrete_map=color_map)
    fig.update_layout(template="plotly_white", height=400, font=dict(size=12))
    out = results_dir / "plot_basis_by_regime.html"
    fig.write_html(str(out))
    return str(out)


def plot_basis_distribution_by_regime(derived_base: Path, results_dir: Path) -> str:
    """standout: distribution of basis by regime (histogram/kde) — shows regime shift clearly."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    pre = df["time"] < pd.Timestamp("2023-03-10", tz="UTC")
    crisis = (df["time"] >= pd.Timestamp("2023-03-10", tz="UTC")) & (df["time"] < pd.Timestamp("2023-03-14", tz="UTC"))
    post = df["time"] >= pd.Timestamp("2023-03-14", tz="UTC")
    df["regime"] = "Post-SVB"
    df.loc[pre, "regime"] = "Pre-SVB"
    df.loc[crisis, "regime"] = "SVB crisis"
    fig = go.Figure()
    for col, label, color in [("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]), ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"])]:
        if col not in df.columns:
            continue
        for regime in ["Pre-SVB", "SVB crisis", "Post-SVB"]:
            sub = df.loc[df["regime"] == regime, col].dropna()
            if sub.empty:
                continue
            fig.add_trace(go.Histogram(x=sub, name=f"{label} – {regime}", opacity=0.6, nbinsx=60, marker_color=color if regime != "SVB crisis" else "#C44536"))
    fig.update_layout(barmode="overlay", title="Basis distribution by regime (standout)", template="plotly_white", height=400, xaxis_title="Basis (bps)", yaxis_title="Count")
    out = results_dir / "plot_basis_distribution_regime.html"
    fig.write_html(str(out))
    return str(out)


def plot_rolling_basis_volatility(derived_base: Path, results_dir: Path) -> str:
    """standout: 1h rolling std of basis — spikes during crisis."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time")
    window = 60
    fig = go.Figure()
    for col, label, color in [("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]), ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"])]:
        if col not in df.columns:
            continue
        r = df[col].rolling(window, min_periods=window // 2).std()
        fig.add_trace(go.Scatter(x=df["time"], y=r, name=label, line=dict(width=2, color=color)))
    for s in _regime_vertical_shapes():
        fig.add_vrect(**s)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(0,0,0,0.3)")
    fig.update_layout(title="Rolling basis volatility (1h std, bps) – standout", xaxis_title="Time (UTC)", yaxis_title="Std (bps)", template="plotly_white", height=400, hovermode="x unified")
    out = results_dir / "plot_rolling_basis_vol.html"
    fig.write_html(str(out))
    return str(out)


def plot_event_study_svb(derived_base: Path, results_dir: Path) -> str:
    """standout: event-study style — basis level in event time (hours around march 10, 12:00 utc)."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    event_ts = pd.Timestamp("2023-03-10 12:00:00", tz="UTC")
    df["event_h"] = (df["time"] - event_ts).dt.total_seconds() / 3600
    sub = df[(df["event_h"] >= -72) & (df["event_h"] <= 72)].copy()
    if sub.empty:
        return ""
    sub = sub.sort_values("event_h")
    fig = go.Figure()
    for col, label, color in [("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]), ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"])]:
        if col not in sub.columns:
            continue
        agg = sub.groupby("event_h")[col].mean().reset_index()
        fig.add_trace(go.Scatter(x=agg["event_h"], y=agg[col], name=label, line=dict(width=2, color=color)))
    fig.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="SVB event (t=0)")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(0,0,0,0.3)")
    fig.update_layout(title="Event study: basis around SVB (t=0 = Mar 10 12:00 UTC)", xaxis_title="Event time (hours)", yaxis_title="Mean basis (bps)", template="plotly_white", height=400, hovermode="x unified")
    out = results_dir / "plot_event_study_svb.html"
    fig.write_html(str(out))
    return str(out)


def plot_exploitable_basis(derived_base: Path, results_dir: Path) -> str:
    """standout: basis net of round-trip cost (e.g. 50 bps). only positive = exploitable."""
    path = derived_base / "basis_1m.parquet"
    if not path.exists():
        return ""
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    cost_bps = 50
    fig = go.Figure()
    for col, label, color in [("basis_usd_usdc_bps", "USD vs USDC", COLORS["usd_usdc"]), ("basis_usd_usdt_bps", "USD vs USDT", COLORS["usd_usdt"])]:
        if col not in df.columns:
            continue
        net = df[col] - cost_bps
        fig.add_trace(go.Scatter(x=df["time"], y=net, name=f"{label} net of {cost_bps} bps cost", line=dict(width=1.8, color=color)))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Zero = break-even after cost")
    for s in _regime_vertical_shapes():
        fig.add_vrect(**s)
    fig.update_layout(title=f"Exploitable basis (basis minus ~{cost_bps} bps round-trip cost)", xaxis_title="Time (UTC)", yaxis_title="Net basis (bps)", template="plotly_white", height=400, hovermode="x unified")
    out = results_dir / "plot_exploitable_basis.html"
    fig.write_html(str(out))
    return str(out)


def build_dashboard(results_dir: Path) -> str:
    """single html dashboard with iframes, news-event links, standout section."""
    basis_ts = results_dir / "plot_basis_timeseries.html"
    stablecoin = results_dir / "plot_stablecoin_discount.html"
    liquidity = results_dir / "plot_liquidity.html"
    basis_regime = results_dir / "plot_basis_by_regime.html"
    dist_regime = results_dir / "plot_basis_distribution_regime.html"
    rolling_vol = results_dir / "plot_rolling_basis_vol.html"
    event_study = results_dir / "plot_event_study_svb.html"
    exploitable = results_dir / "plot_exploitable_basis.html"

    def iframe_block(name: Path, height=460) -> str:
        if not name.exists():
            return f"<p>Not generated (run pipeline first): {name.name}</p>"
        return f'<iframe src="{name.name}" class="plot-iframe" style="height:{height}px"></iframe>'

    basis_csv = results_dir / "basis_summary_by_regime.csv"
    table1 = ""
    if basis_csv.exists():
        df = pd.read_csv(basis_csv)
        table1 = df.to_html(index=False, classes="table table-sm")

    news_rows = []
    verified_events = _load_news_events(verify_links=True)
    for ts, title, url in verified_events:
        news_rows.append(f'<tr><td>{ts.strftime("%Y-%m-%d %H:%M")} UTC</td><td><a href="{url}" target="_blank" rel="noopener">{title}</a></td></tr>')
    news_table = "<table class=\"table\"><thead><tr><th>Time (UTC)</th><th>Headline (click for article)</th></tr></thead><tbody>" + "".join(news_rows) + "</tbody></table>" if news_rows else "<p>No verified links (run pipeline with network access to check URLs). Add events in <code>data/supplementary/news_events.csv</code>.</p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IAQF 2026 – Cross-Currency Dynamics Results</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 1rem; }}
    h1 {{ color: #1a1a2e; }}
    h2 {{ margin-top: 2rem; color: #16213e; }}
    h3 {{ margin-top: 1.2rem; color: #333; }}
    .table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
    .table th, .table td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
    .table th {{ background: #eee; }}
    .table a {{ color: #0173B2; }}
    .plot-iframe {{ border: none; width: 100%; display: block; margin: 1rem 0; }}
    .plot {{ margin: 1rem 0; }}
    .standout {{ background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-top: 1rem; }}
  </style>
</head>
<body>
  <h1>Cross-Currency Dynamics in Cryptocurrency Markets</h1>
  <p><strong>Cross-Currency Dynamics in Cryptocurrencies under Stablecoin Regulation</strong></p>
  <p>Window: March 1–21, 2023 (UTC). Base asset: BTC. Exchanges: Coinbase, Binance, Kraken.</p>

  <h2>Q1: Cross-Currency Basis</h2>
  <p>BTC/USD vs BTC/USDT vs BTC/USDC (basis in bps). Dashed vertical lines = news events; click headlines below for articles.</p>
  <div class="plot">{iframe_block(basis_ts, 500)}</div>
  <h3>News & events (click to open article)</h3>
  {news_table}
  <h3>Summary by regime</h3>
  {table1 if table1 else "<p>Run analysis to generate basis_summary_by_regime.csv</p>"}
  <div class="plot">{iframe_block(basis_regime)}</div>

  <h2>Standout: Extra insight plots</h2>
  <div class="standout">
  <p>Basis distribution by regime, rolling volatility, event-study around SVB, and exploitable basis (net of transaction cost).</p>
  <div class="plot">{iframe_block(dist_regime)}</div>
  <div class="plot">{iframe_block(rolling_vol)}</div>
  <div class="plot">{iframe_block(event_study)}</div>
  <div class="plot">{iframe_block(exploitable)}</div>
  </div>

  <h2>Q2: Stablecoin Dynamics</h2>
  <p>Implied USDC/USDT discount from peg (1.00) during SVB event.</p>
  <div class="plot">{iframe_block(stablecoin)}</div>

  <h2>Q3: Liquidity & Fragmentation</h2>
  <p>High-low spread proxy and volume by exchange and pair (1h resampled).</p>
  <div class="plot">{iframe_block(liquidity)}</div>

  <h2>Q4: Regulatory Overlay</h2>
  <p>See <code>results/regulatory_overlay.md</code> for mapping of findings to GENIUS Act and policy implications.</p>
</body>
</html>
"""
    out = results_dir / "dashboard.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return str(out)


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    derived_base = root / config["paths"]["derived"]
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("Building interactive plots...")
    plot_basis_timeseries(derived_base, results_dir)
    plot_stablecoin_discount(derived_base, results_dir)
    plot_liquidity_by_quote(derived_base, results_dir)
    plot_basis_by_regime(results_dir)
    print("Building standout plots...")
    plot_basis_distribution_by_regime(derived_base, results_dir)
    plot_rolling_basis_volatility(derived_base, results_dir)
    plot_event_study_svb(derived_base, results_dir)
    plot_exploitable_basis(derived_base, results_dir)
    print("Verifying news links for dashboard (may take a moment)...")
    path = build_dashboard(results_dir)
    print(f"Dashboard: {path}")


if __name__ == "__main__":
    run()
