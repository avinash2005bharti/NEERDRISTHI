from datetime import datetime, timezone
from typing import Optional, Literal
from ..config import settings


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        # Handle trailing Z or timezone offsets
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def calculate_freshness(
    observed_at_str: Optional[str],
    max_minutes: Optional[int] = None
) -> Literal["fresh", "stale", "unknown"]:
    if not observed_at_str:
        return "unknown"

    dt = parse_iso_datetime(observed_at_str)
    if not dt:
        return "unknown"

    limit_minutes = max_minutes if max_minutes is not None else settings.MAX_DATA_FRESHNESS_MINUTES
    now = datetime.now(timezone.utc)
    delta_minutes = (now - dt).total_seconds() / 60.0

    if delta_minutes < 0:
        # Future forecast, valid if within reasonable horizon (e.g. 7 days)
        return "fresh" if abs(delta_minutes) <= (7 * 24 * 60) else "stale"

    return "fresh" if delta_minutes <= limit_minutes else "stale"


def is_within_validity(valid_from: Optional[str], valid_to: Optional[str]) -> bool:
    now = datetime.now(timezone.utc)
    if valid_from:
        start_dt = parse_iso_datetime(valid_from)
        if start_dt and now < start_dt:
            return False
    if valid_to:
        end_dt = parse_iso_datetime(valid_to)
        if end_dt and now > end_dt:
            return False
    return True
