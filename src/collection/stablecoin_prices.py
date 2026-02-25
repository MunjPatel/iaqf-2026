"""
§2.4 Supplementary data: USDC/USD and USDT/USD peg prices (e.g. CoinGecko market_chart/range).
Optional: implement when needed for event-study validation.
"""
from src.utils import get_project_root, load_config


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    out_dir = root / config["paths"]["supplementary"]
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Stablecoin peg prices: not implemented. Use CoinGecko API when needed.")


if __name__ == "__main__":
    run()
