"""Shared helpers for collection and cleaning."""
from datetime import datetime, timezone

# Problem statement: March 1–21, 2023 includes USDC de-peg (SVB).
SVB_ANNOUNCE_UTC = datetime(2023, 3, 10, 0, 0, 0, tzinfo=timezone.utc)   # SVB failure announced
USDC_DEPEG_TROUGH_UTC = datetime(2023, 3, 11, 0, 0, 0, tzinfo=timezone.utc)  # USDC trough ~March 11


def parse_window(config: dict) -> tuple:
    """Return (start_utc, end_utc) for the 21-day window."""
    start = datetime.fromisoformat(config["start_date"] + "T00:00:00").replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(config["end_date"] + "T00:00:00").replace(tzinfo=timezone.utc)
    return start, end
