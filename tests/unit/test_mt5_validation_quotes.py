"""Session-aware quote staleness tests (02-02 Task 2: D-57; research §3 table).

Labelled fixtures (``FIXTURE_`` prefix, tests-only) — never live data.
Every session row carries a ±1s boundary pair; the weekend window exempts
regardless of age.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from goldmasters_contracts import MarketQuote, QualityStatus

from services.mt5_adapter.validation import (
    is_weekend_closed,
    quote_stale_limit_for,
    session_for,
    validate_quote,
)

WEEKEND_SPEC = "Fri 21:00-Sun 22:00"

LIMITS = {"overlap": 30, "major": 60, "asia": 180, "offhours": 300}

WINDOWS = {
    "overlap_windows": "13:00-16:30",
    "major_windows": "08:00-13:00,16:30-21:00",
    "asia_windows": "00:00-08:00",
}


def FIXTURE_quote(  # noqa: N802 - fixture prefix is the labelling convention
    instant: datetime,
) -> MarketQuote:
    return MarketQuote(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        bid=Decimal("2387.1"),
        bid_time=instant,
        ask=Decimal("2387.45"),
        ask_time=instant,
        last=None,
        last_time=None,
        spread=Decimal("0.35"),
        retrieved_at=instant,
        quality_status=QualityStatus.NOT_EVALUATED,
    )


def _limit_at(moment: datetime) -> int:
    return quote_stale_limit_for(
        moment,
        overlap=LIMITS["overlap"],
        major=LIMITS["major"],
        asia=LIMITS["asia"],
        offhours=LIMITS["offhours"],
        **WINDOWS,
    )


def _stamped(instant: datetime, now: datetime) -> MarketQuote:
    return validate_quote(
        FIXTURE_quote(instant),
        now_utc=now,
        stale_seconds=_limit_at(now),
        weekend_spec=WEEKEND_SPEC,
    )


def test_session_table_matches_research() -> None:
    tuesday = datetime(2026, 1, 6, tzinfo=UTC)
    assert session_for(tuesday + timedelta(hours=14), **WINDOWS) == "overlap"
    assert session_for(tuesday + timedelta(hours=10), **WINDOWS) == "major"
    assert session_for(tuesday + timedelta(hours=18), **WINDOWS) == "major"
    assert session_for(tuesday + timedelta(hours=4), **WINDOWS) == "asia"
    assert session_for(tuesday + timedelta(hours=22), **WINDOWS) == "offhours"
    assert _limit_at(tuesday + timedelta(hours=14)) == 30
    assert _limit_at(tuesday + timedelta(hours=10)) == 60
    assert _limit_at(tuesday + timedelta(hours=4)) == 180
    assert _limit_at(tuesday + timedelta(hours=22)) == 300


def test_overlap_boundary_pm1s() -> None:
    """Overlap tick at 30s∓1s around a 14:00 UTC retrieval."""
    now = datetime(2026, 1, 6, 14, 0, 0, tzinfo=UTC)
    fresh = _stamped(now - timedelta(seconds=29), now)
    assert fresh.quality_status == QualityStatus.OK
    stale = _stamped(now - timedelta(seconds=31), now)
    assert stale.quality_status == QualityStatus.STALE
    assert QualityStatus.STALE in stale.quality_flags


def test_major_boundary_pm1s() -> None:
    now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
    assert _stamped(now - timedelta(seconds=59), now).quality_status == QualityStatus.OK
    stale = _stamped(now - timedelta(seconds=61), now)
    assert stale.quality_status == QualityStatus.STALE


def test_asia_boundary_pm1s() -> None:
    now = datetime(2026, 1, 6, 4, 0, 0, tzinfo=UTC)
    assert _stamped(now - timedelta(seconds=179), now).quality_status == QualityStatus.OK
    assert _stamped(now - timedelta(seconds=181), now).quality_status == QualityStatus.STALE


def test_offhours_boundary_pm1s() -> None:
    now = datetime(2026, 1, 6, 22, 0, 0, tzinfo=UTC)
    assert _stamped(now - timedelta(seconds=299), now).quality_status == QualityStatus.OK
    assert _stamped(now - timedelta(seconds=301), now).quality_status == QualityStatus.STALE


def test_weekend_tick_is_unavailable_never_stale() -> None:
    """A Saturday tick reads disconnected regardless of age — even when fresh."""
    saturday = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    assert is_weekend_closed(saturday, WEEKEND_SPEC)
    aged = _stamped(saturday - timedelta(hours=30), saturday)
    assert aged.quality_status == QualityStatus.DISCONNECTED
    assert QualityStatus.STALE not in aged.quality_flags
    fresh = _stamped(saturday - timedelta(seconds=5), saturday)
    assert fresh.quality_status == QualityStatus.DISCONNECTED


def test_session_boundaries_are_settings_driven() -> None:
    """Overriding the overlap window moves the boundary with it."""
    now = datetime(2026, 1, 6, 14, 0, 0, tzinfo=UTC)
    moved = {
        "overlap_windows": "13:00-14:00",
        "major_windows": "08:00-13:00,14:00-21:00",
        "asia_windows": "00:00-08:00",
    }
    assert session_for(now, **moved) == "major"
    limit = quote_stale_limit_for(
        now,
        overlap=30,
        major=60,
        asia=180,
        offhours=300,
        **moved,
    )
    assert limit == 60


def test_malformed_window_spec_fails_closed() -> None:
    import pytest

    from services.mt5_adapter.validation import parse_session_windows

    with pytest.raises(ValueError, match="13:00"):
        session_for(
            datetime(2026, 1, 6, 14, tzinfo=UTC),
            overlap_windows="13:00",
            major_windows="08:00-13:00",
            asia_windows="00:00-08:00",
        )
    with pytest.raises(ValueError):
        parse_session_windows("")
