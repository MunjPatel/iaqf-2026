"""Load config.yaml from project root."""
from pathlib import Path
from typing import Optional
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_project_root() -> Path:
    return _PROJECT_ROOT


def load_config(config_path: Optional[Path] = None) -> dict:
    path = config_path or (_PROJECT_ROOT / "config.yaml")
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
