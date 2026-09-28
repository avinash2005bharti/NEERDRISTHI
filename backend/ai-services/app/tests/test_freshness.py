from datetime import datetime, timezone, timedelta
from app.utils.freshness import calculate_freshness, is_within_validity


def test_recent_observation_is_fresh():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(minutes=30)).isoformat()
    assert calculate_freshness(recent, max_minutes=360) == "fresh"


def test_old_observation_is_stale():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=8)).isoformat()
    assert calculate_freshness(old, max_minutes=360) == "stale"


def test_empty_timestamp_is_unknown():
    assert calculate_freshness(None) == "unknown"
    assert calculate_freshness("") == "unknown"


def test_is_within_validity():
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=2)).isoformat()
    end = (now + timedelta(hours=4)).isoformat()
    assert is_within_validity(start, end) is True

    expired_end = (now - timedelta(minutes=10)).isoformat()
    assert is_within_validity(start, expired_end) is False
