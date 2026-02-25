# IAQF Student Competition 2026

**Cross-Currency Dynamics in Cryptocurrencies under Stablecoin Regulation**

This repository contains our submission: a **10-page paper** and **reproducible code** for data collection, processing, and analysis. The sample covers March 1–21, 2023 (UTC) and includes the Silicon Valley Bank (SVB) failure and USDC de-peg.

---

## Deliverables (competition requirements)

Per IAQF rules: the **solution** is at most **10 pages**, single-sided, **Times New Roman 12pt**, and must contain **no reference to school, students, or team name** (blind judging). The **code** is submitted as a **separate addendum**, not in the 10 pages. See **SUBMISSION_CHECKLIST.md** for the full checklist and submission address.

1. **Solution PDF** (`paper/main.tex` → PDF) with:
   - Financial context and motivation (including regulatory background)
   - Data description and methodology
   - Empirical results on cross-currency pricing and liquidity
   - Discussion of how stablecoin regulation and market structure affect observed patterns
   - Conclusions and implications for trading, risk management, and policy

2. **Code addendum** (this repo), submitted separately, with clear reproduction instructions below.

---

## How to reproduce the results (step by step)

### Prerequisites

- **Python 3.9+**
- **Network access** (for data collection and optional link verification)
- No API keys required (we use public exchange APIs)

### 1. Clone and install

```bash
cd iaqf-2026
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set the project root (so imports work)

From the **project root** (`iaqf-2026/`), set `PYTHONPATH` to the current directory:

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH = (Get-Location).Path
```

**macOS/Linux:**
```bash
export PYTHONPATH=$(pwd)
```

Keep this terminal in the project root for all following commands.

### 3. Collect raw data

This step downloads 1-minute candles from the exchanges for March 1–21, 2023. It takes a few minutes and requires internet.

```bash
python -m src.collection.coinbase
python -m src.collection.binance
```

Optional (if you have Kraken historical data or use a provider):  
`python -m src.collection.kraken`

- **Coinbase**: BTC-USD, BTC-USDT, BTC-USDC → `data/raw/coinbase/`
- **Binance**: BTCUSDT, BTCUSDC → `data/raw/binance/`

### 4. Run the full pipeline

One command runs cleaning, alignment, basis and liquidity computation, analysis, visualizations, and export of paper tables:

```bash
python run_all.py
```

This will:

- Clean raw data and align exchanges
- Compute cross-currency basis and liquidity metrics
- Run the four-question analysis (basis, stablecoin dynamics, liquidity, regulatory overlay)
- Build the interactive dashboard and Plotly figures
- Verify news links and export LaTeX tables for the paper

Outputs:

- **Results and dashboard**: `results/dashboard.html` (open in a browser)
- **Tables**: `results/*.csv` and `paper/tables/*.tex`
- **Figures**: `results/plot_*.html` (interactive)

### 5. Build the paper (PDF)

From the project root:

```bash
cd paper
pdflatex main.tex
pdflatex main.tex
cd ..
```

The PDF is `paper/main.pdf`. It uses the tables in `paper/tables/`, which are generated from the same CSVs in `results/` that the dashboard uses, so the paper and the code stay in sync.

### 6. Optional: export tables only (if you already ran the pipeline)

If you only want to refresh the LaTeX tables (e.g. after editing CSVs):

```bash
python scripts/export_paper_tables.py
```

---

## What you get after reproduction

| Output | Description |
|--------|-------------|
| `results/dashboard.html` | Interactive dashboard: basis, stablecoin discount, liquidity, news links, standout plots |
| `results/*.csv` | Basis and stablecoin summary by regime, liquidity by exchange/regime |
| `results/plot_*.html` | Individual interactive Plotly figures |
| `paper/main.pdf` | 10-page paper (after running `pdflatex` in `paper/`) |
| `paper/tables/*.tex` | LaTeX tables generated from `results/*.csv` |

---

## Configuration

- **Sample window and paths**: `config.yaml` (default March 1–21, 2023; paths under `data/` and `results/`).
- **News events**: `data/supplementary/news_events.csv` (date_utc, title, url). Only links that return HTTP 200 are shown on the dashboard.

---

## Directory structure

```
iaqf-2026/
├── config.yaml
├── requirements.txt
├── run_all.py              # Single pipeline entry point
├── README.md               # This file
├── data/
│   ├── raw/                # Raw API responses (gitignored)
│   ├── clean/               # Cleaned and aligned parquet
│   ├── derived/             # Basis, returns, liquidity
│   └── supplementary/       # news_events.csv
├── results/                 # All analysis outputs
│   ├── dashboard.html
│   ├── plot_*.html
│   └── *.csv
├── paper/
│   ├── main.tex             # 10-page paper source
│   └── tables/              # Generated .tex tables
├── scripts/
│   └── export_paper_tables.py
└── src/
    ├── collection/          # coinbase, binance, kraken
    ├── cleaning/            # clean_candles, align_exchanges
    ├── features/            # basis, returns, liquidity
    ├── analysis/            # run_analysis (4 questions)
    ├── visualization/       # Plotly plots, dashboard, news
    └── utils/
```

---

## Problem summary (competition)

1. **Cross-currency basis**: How does BTC/USDT compare to BTC/USD over time? Do we see persistent differences after transaction costs?
2. **Stablecoin dynamics**: How do premium/discount patterns (e.g. USDT vs USDC) vary across exchanges and regimes? How might U.S. regulation affect confidence?
3. **Liquidity & fragmentation**: Does liquidity differ across quote currencies? How do spread and volatility vary between USD- and stablecoin-quoted BTC?
4. **Regulatory overlay**: Tie empirical findings to the GENIUS Act and stablecoin settlement (e.g. Visa USDC).

Our paper and dashboard answer these using the March 2023 SVB/USDC episode and the data pipeline above.
