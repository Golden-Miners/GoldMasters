"""Weekend-gap vs missing-history classifier tests (02-02 Task 3: D-58).

Labelled fixtures (``FIXTURE_`` prefix, tests-only) — never live data.
Weekend absence is expected-and-flagged; mid-week absence is missing-history;
the daily-break window tolerates one adjacent bar; reopen resumes clean.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from goldmasters_contracts import (
    MarketBar,
    QualityStatus,
    Timeframe,
    VolumeType,
)

from services.mt5_adapter.validation import (
    classify_gap,
    is_weekend_closed,
    missing_opens,
    validate_bars,
)

WEEKEND_SPEC = "Fri 21:00-Sun 22:00"
BREAK_SPEC = "21:00-22:00"


def FIXTURE_bar(open_time: datetime) -> MarketBar:  # noqa: N802
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=open_time,
        bar_close_time=open_time + timedelta(hours=1),
        open=Decimal("2381.00"),
        high=Decimal("2383.00"),
        low=Decimal("2380.00"),
        close=Decimal("2382.00"),
        volume=Decimal(100),
        volume_type=VolumeType.TICK,
        retrieved_at=open_time + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.NOT_EVALUATED,
    )


def FIXTURE_friday_2100() -> datetime:  # noqa: N802
    """A Friday 21:00 UTC — the weekend window opens here."""
    return datetime(2026, 1, 9, 21, 0, tzinfo=UTC)


def _stamped(bars: list[MarketBar], now: datetime) -> list[MarketBar]:
    return validate_bars(
        bars,
        now_utc=now,
        stale_closed_bars=2,
        stale_grace_seconds=300,
        weekend_spec=WEEKEND_SPEC,
        break_spec=BREAK_SPEC,
    )


def test_weekend_window_boundaries() -> None:
    assert is_weekend_closed(FIXTURE_friday_2100(), WEEKEND_SPEC)
    assert is_weekend_closed(datetime(2026, 1, 10, 12, tzinfo=UTC), WEEKEND_SPEC)
    assert not is_weekend_closed(datetime(2026, 1, 11, 22, tzinfo=UTC), WEEKEND_SPEC)
    assert not is_weekend_closed(datetime(2026, 1, 9, 20, tzinfo=UTC), WEEKEND_SPEC)
    assert not is_weekend_closed(datetime(2026, 1, 6, 12, tzinfo=UTC), WEEKEND_SPEC)


def test_weekend_gap_is_expected_and_flagged() -> None:
    """Fri 20:00 → Sun 22:00 flanks: gap flags, no missing-history."""
    friday = FIXTURE_bar(datetime(2026, 1, 9, 20, 0, tzinfo=UTC))
    sunday = FIXTURE_bar(datetime(2026, 1, 11, 22, 0, tzinfo=UTC))
    missing = missing_opens(friday.bar_open_time, sunday.bar_open_time)
    assert len(missing) > 24
    assert classify_gap(missing, weekend_spec=WEEKEND_SPEC, break_spec=BREAK_SPEC) == "expected"
    stamped = _stamped([friday, sunday], datetime(2026, 1, 11, 23, 30, tzinfo=UTC))
    assert QualityStatus.GAP in stamped[1].quality_flags
    assert QualityStatus.MISSING_HISTORY not in stamped[1].quality_flags


def test_midweek_gap_is_missing_history() -> None:
    tuesday = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    bars = [FIXTURE_bar(tuesday), FIXTURE_bar(tuesday + timedelta(hours=3))]
    missing = missing_opens(bars[0].bar_open_time, bars[1].bar_open_time)
    assert classify_gap(missing, weekend_spec=WEEKEND_SPEC, break_spec=BREAK_SPEC) == (
        "missing-history"
    )
    stamped = _stamped(bars, tuesday + timedelta(hours=4))
    assert stamped[1].quality_status == QualityStatus.MISSING_HISTORY


def test_short_backfill_is_missing_history() -> None:
    """Fewer closed bars than requested outside closed windows: no silent pass."""
    tuesday = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    stamped = _stamped([FIXTURE_bar(tuesday)], tuesday + timedelta(hours=2))
    assert stamped[0].quality_status == QualityStatus.OK
    # ...but a two-bar hole next to it is missing-history, not an expected gap.
    other = FIXTURE_bar(tuesday + timedelta(hours=3))
    stamped = _stamped([FIXTURE_bar(tuesday), other], tuesday + timedelta(hours=4))
    assert stamped[1].quality_status == QualityStatus.MISSING_HISTORY


def test_break_adjacent_single_gap_tolerated_two_bar_gap_is_not() -> None:
    """One bar beside the 21:00–22:00 break is expected; two bars are not."""
    monday = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)
    single = [monday, monday + timedelta(hours=2)]  # 20:00 missing, break-adjacent
    missing = missing_opens(*single)
    assert classify_gap(missing, weekend_spec=WEEKEND_SPEC, break_spec=BREAK_SPEC) == "expected"
    stamped = _stamped(
        [FIXTURE_bar(single[0]), FIXTURE_bar(single[1])], monday + timedelta(hours=3)
    )
    assert QualityStatus.GAP in stamped[1].quality_flags
    double = [monday, monday + timedelta(hours=3)]  # 20:00 + 21:00 missing
    missing2 = missing_opens(*double)
    assert classify_gap(missing2, weekend_spec=WEEKEND_SPEC, break_spec=BREAK_SPEC) == (
        "missing-history"
    )


def test_reopen_resumes_clean() -> None:
    """First post-weekend retrieval validates without carrying weekend flags."""
    sunday = FIXTURE_bar(datetime(2026, 1, 11, 22, 0, tzinfo=UTC))
    monday = FIXTURE_bar(datetime(2026, 1, 11, 23, 0, tzinfo=UTC))
    stamped = _stamped([sunday, monday], datetime(2026, 1, 12, 0, 30, tzinfo=UTC))
    assert all(b.quality_status == QualityStatus.OK for b in stamped)
