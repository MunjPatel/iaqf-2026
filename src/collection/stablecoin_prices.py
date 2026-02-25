"""supplementary: usdc/usd and usdt/usd peg prices (e.g. coingecko). we left this optional for now."""
from src.utils import get_project_root, load_config


def run(config=None):
    config = config or load_config()
    root = get_project_root()
    out_dir = root / config["paths"]["supplementary"]
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Stablecoin peg prices: not implemented. Use CoinGecko API when needed.")


if __name__ == "__main__":
    run()
