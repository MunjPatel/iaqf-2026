"""shared helpers for collection and cleaning."""
from datetime import datetime, timezone

# our sample: march 1–21, 2023 includes usdc de-peg (svb)
SVB_ANNOUNCE_UTC = datetime(2023, 3, 10, 0, 0, 0, tzinfo=timezone.utc)   # svb failure announced
USDC_DEPEG_TROUGH_UTC = datetime(2023, 3, 11, 0, 0, 0, tzinfo=timezone.utc)  # usdc trough ~march 11


def parse_window(config: dict) -> tuple:
    """return (start_utc, end_utc) for our 21-day window."""
    start = datetime.fromisoformat(config["start_date"] + "T00:00:00").replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(config["end_date"] + "T00:00:00").replace(tzinfo=timezone.utc)
    return start, end
