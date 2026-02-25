"""Load news/event timeline for March 2023 SVB/USDC. Verify links before showing on dashboard."""
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from src.utils import get_project_root, load_config

# User-Agent so servers don't block the check
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"}


def load_news_events(config=None, verify_links=False) -> List[Tuple]:
    """Return list of (timestamp_utc, title, url). If verify_links=True, only return URLs that return HTTP 200."""
    config = config or load_config()
    root = get_project_root()
    path = root / config["paths"]["supplementary"] / "news_events.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["date_utc"], utc=True)
    out = []
    for _, row in df.iterrows():
        url = (row["url"] or "").strip()
        if not url:
            continue
        out.append((row["ts"], row["title"], url))
    if verify_links:
        out = _keep_only_working_links(out)
    return out


def _keep_only_working_links(events: List[Tuple], timeout_sec: int = 10) -> List[Tuple]:
    """Keep only (ts, title, url) where url returns HTTP 200."""
    try:
        import requests
    except ImportError:
        return events
    result = []
    for ts, title, url in events:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=timeout_sec, allow_redirects=True)
            if r.status_code == 200:
                result.append((ts, title, url))
        except Exception:
            pass
    return result
