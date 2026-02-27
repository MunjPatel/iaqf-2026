"""export result csvs to latex tables for the paper. we run from project root with PYTHONPATH set so the paper numbers match our code output."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results"
PAPER_TABLES = ROOT / "paper" / "tables"
PAPER_TABLES.mkdir(parents=True, exist_ok=True)


def export_basis_summary():
    path = RESULTS / "basis_summary_by_regime.csv"
    if not path.exists():
        print(f"Skip: {path} not found. Run run_all.py first.")
        return
    import pandas as pd
    df = pd.read_csv(path)
    # regime order for display
    regime_order = ["Pre-SVB (Mar 1-9)", "SVB crisis (Mar 10-13)", "Post-SVB (Mar 14-21)"]
    df["regime"] = pd.Categorical(df["regime"], categories=regime_order, ordered=True)
    df = df.sort_values(["basis", "regime"])
    rows = []
    rows.append("\\begin{tabular}{llrrrrr}")
    rows.append("\\toprule")
    rows.append("Basis & Regime & Mean (bps) & Std & Median & Min & Max \\\\")
    rows.append("\\midrule")
    for _, r in df.iterrows():
        reg = r["regime"].replace("--", "---")
        rows.append(f"{r['basis']} & {reg} & {r['mean_bps']:.2f} & {r['std_bps']:.2f} & {r['median_bps']:.2f} & {r['min_bps']:.2f} & {r['max_bps']:.2f} \\\\")
    rows.append("\\bottomrule")
    rows.append("\\end{tabular}")
    out = PAPER_TABLES / "basis_summary.tex"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    print(f"Wrote {out}")


def export_stablecoin_summary():
    path = RESULTS / "stablecoin_discount_by_regime.csv"
    if not path.exists():
        print(f"Skip: {path} not found.")
        return
    import pandas as pd
    df = pd.read_csv(path)
    regime_order = ["Pre-SVB", "SVB crisis", "Post-SVB"]
    df["regime"] = pd.Categorical(df["regime"], categories=regime_order, ordered=True)
    df = df.sort_values(["metric", "regime"])
    rows = []
    rows.append("\\begin{tabular}{llrrr}")
    rows.append("\\toprule")
    rows.append("Metric & Regime & Mean (bps) & Std & Median \\\\")
    rows.append("\\midrule")
    for _, r in df.iterrows():
        metric = "USDC discount" if "usdc" in str(r["metric"]) else "USDT discount"
        rows.append(f"{metric} & {r['regime']} & {r['mean_bps']:.2f} & {r['std_bps']:.2f} & {r['median_bps']:.2f} \\\\")
    rows.append("\\bottomrule")
    rows.append("\\end{tabular}")
    out = PAPER_TABLES / "stablecoin_summary.tex"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    print(f"Wrote {out}")


def main():
    export_basis_summary()
    export_stablecoin_summary()
    print("We exported the paper tables. Run pdflatex twice in paper/ to rebuild the PDF.")


if __name__ == "__main__":
    main()
