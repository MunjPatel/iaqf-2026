"""single pipeline entry point: clean, align, basis, returns, liquidity, analysis, visualizations, dashboard. we open results/dashboard.html in a browser for interactive plots."""
import sys
from pathlib import Path

# run from project root with PYTHONPATH set to project root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cleaning import clean_candles, align_exchanges
from src.features import basis, returns, liquidity
from src.analysis import run_analysis
from src.visualization import plots


def main():
    print("=== IAQF 2026 Pipeline ===\n")
    print("1. Cleaning raw candles...")
    clean_candles.run()
    print("\n2. Aligning exchanges...")
    align_exchanges.run()
    print("\n3. Computing basis...")
    basis.run()
    print("\n4. Computing returns...")
    returns.run()
    print("\n5. Computing liquidity metrics...")
    liquidity.run()
    print("\n6. Running analysis (4 questions)...")
    run_analysis.run()
    print("\n7. Building interactive visualizations and dashboard...")
    plots.run()
    print("\n8. Exporting paper tables (for LaTeX)...")
    try:
        import runpy
        runpy.run_path(str(ROOT / "scripts" / "export_paper_tables.py"), init_globals={"__name__": "__main__"}, run_name="__main__")
    except Exception as e:
        print(f"   (Paper tables skip: {e})")
    print("\n9. Exporting paper figures (PNG for LaTeX)...")
    try:
        import runpy
        runpy.run_path(str(ROOT / "scripts" / "export_paper_figures.py"), init_globals={"__name__": "__main__"}, run_name="__main__")
    except Exception as e:
        print(f"   (Paper figures skip; install kaleido: {e})")
    print("\nDone. We built the dashboard at results/dashboard.html. Run pdflatex twice in paper/ to build the PDF.")


if __name__ == "__main__":
    main()
