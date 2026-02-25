# IAQF 2026 — make collect → clean → features → analysis → figures → paper (§6.3)
PYTHON = python
ROOT = .

collect:
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.collection.coinbase
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.collection.binance
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.collection.kraken

clean:
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.cleaning.clean_candles
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.cleaning.align_exchanges

features:
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.features.basis
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.features.returns
	cd $(ROOT) && set PYTHONPATH=$(ROOT) && $(PYTHON) -m src.features.liquidity

analysis:
	@echo "Run analysis modules (regime_switching, event_study, panel_regression, etc.) as needed."

figures:
	@echo "Run visualization scripts to export to paper/figures/."

paper:
	cd paper && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex

all: collect clean features analysis figures paper
