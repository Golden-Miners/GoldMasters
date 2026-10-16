"""Split enforcement: IS/VS/OOS separation with honest gap reporting (06-02 Task 1).

Boundaries are UTC datetimes; the display timezone never affects
classification (DST-crossing proof). Missing bars are reported into the
quality report plus excluded periods — never synthesised (R-01, T-06-06).
Out-of-window bars are rejected, and the runner refuses them (criterion 3).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import (
    MarketBar,
    QualityStatus,
    Timeframe,
    VolumeType,
)

from src.goldmasters.backtest.splits import (
    SplitWindows,
    classify_bar,
    enforce_splits,
    timeframe_step,
)

IS_START = datetime(2026, 1, 1, tzinfo=UTC)
IS_END = datetime(2026, 3, 1, tzinfo=UTC)
VS_START = IS_END
VS_END = datetime(2026, 5, 1, tzinfo=UTC)
OOS_START = VS_END
OOS_END = datetime(2026, 7, 1, tzinfo=UTC)


def _windows(display_timezone: str = "UTC") -> SplitWindows:
    return SplitWindows(
        in_sample_start=IS_START,
        in_sample_end=IS_END,
        validation_start=VS_START,
        validation_end=VS_END,
        out_of_sample_start=OOS_START,
        out_of_sample_end=OOS_END,
        display_timezone=display_timezone,
    )


def _bar(open_time: datetime, close: str = "100") -> MarketBar:
    """FIXTURE bar: labelled test vector, never live data."""
    close_d = Decimal(close)
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=open_time,
        bar_close_time=open_time + timedelta(hours=1),
        open=close_d,
        high=close_d + Decimal(1),
        low=close_d - Decimal(1),
        close=close_d,
        volume=Decimal(10),
        volume_type=VolumeType.TICK,
        retrieved_at=open_time + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.OK,
    )


def _hourly(start: datetime, count: int) -> list[MarketBar]:
    return [_bar(start + timedelta(hours=index)) for index in range(count)]


def test_windows_reject_naive_datetimes() -> None:
    naive = datetime(2026, 1, 1)
    with pytest.raises(ValueError, match="timezone-aware"):
        SplitWindows(
            in_sample_start=naive,
            in_sample_end=IS_END,
            validation_start=VS_START,
            validation_end=VS_END,
            out_of_sample_start=OOS_START,
            out_of_sample_end=OOS_END,
        )


def test_dst_crossing_boundary_classifies_by_utc() -> None:
    """EU spring-forward (2026-03-29 01:00Z): display zone changes nothing."""
    windows_utc = SplitWindows(
        in_sample_start=datetime(2026, 3, 1, tzinfo=UTC),
        in_sample_end=datetime(2026, 3, 29, 1, 30, tzinfo=UTC),
        validation_start=datetime(2026, 3, 29, 1, 30, tzinfo=UTC),
        validation_end=datetime(2026, 4, 1, tzinfo=UTC),
        out_of_sample_start=datetime(2026, 4, 1, tzinfo=UTC),
        out_of_sample_end=datetime(2026, 5, 1, tzinfo=UTC),
        display_timezone="UTC",
    )
    windows_berlin = SplitWindows(
        in_sample_start=datetime(2026, 3, 1, tzinfo=UTC),
        in_sample_end=datetime(2026, 3, 29, 1, 30, tzinfo=UTC),
        validation_start=datetime(2026, 3, 29, 1, 30, tzinfo=UTC),
        validation_end=datetime(2026, 4, 1, tzinfo=UTC),
        out_of_sample_start=datetime(2026, 4, 1, tzinfo=UTC),
        out_of_sample_end=datetime(2026, 5, 1, tzinfo=UTC),
        display_timezone="Europe/Berlin",
    )
    straddlers = _hourly(datetime(2026, 3, 29, 0, 0, tzinfo=UTC), 4)
    utc_labels = [classify_bar(bar.bar_close_time, windows_utc) for bar in straddlers]
    berlin_labels = [classify_bar(bar.bar_close_time, windows_berlin) for bar in straddlers]
    assert utc_labels == berlin_labels
    assert utc_labels[0] == "in_sample"  # close 01:00Z < 01:30Z boundary
    assert utc_labels[1:] == ["validation"] * 3  # closes 02:00Z+ past the boundary


def test_gap_bars_reported_not_filled() -> None:
    bars = _hourly(datetime(2026, 1, 5, tzinfo=UTC), 4)
    gap_bars = bars[:2] + _hourly(datetime(2026, 1, 5, 4, 0, tzinfo=UTC), 2)
    enforcement = enforce_splits(gap_bars, _windows(), Timeframe.H1)
    assert len(enforcement.in_window) == 4
    assert len(enforcement.missing_bars) == 1
    assert enforcement.missing_bars[0]["bars_skipped"] == "2"
    assert enforcement.excluded_periods, "gaps must surface as excluded periods"
    assert any("never synthesised" in period["reason"] for period in enforcement.excluded_periods)
    assert any("gap" in flag for flag in enforcement.quality_flags)


def test_excluded_periods_empty_without_gaps() -> None:
    enforcement = enforce_splits(
        _hourly(datetime(2026, 1, 5, tzinfo=UTC), 4), _windows(), Timeframe.H1
    )
    assert enforcement.excluded_periods == ()
    assert enforcement.missing_bars == ()


def test_out_of_window_bar_rejected() -> None:
    stray = _bar(datetime(2025, 12, 31, 12, 0, tzinfo=UTC))
    assert classify_bar(stray.bar_close_time, _windows()) is None
    enforcement = enforce_splits(
        [stray, _bar(datetime(2026, 1, 5, tzinfo=UTC))], _windows(), Timeframe.H1
    )
    assert enforcement.out_of_window == (stray,)
    assert any("out-of-window" in flag for flag in enforcement.quality_flags)


def test_misordered_bars_raise() -> None:
    bars = _hourly(datetime(2026, 1, 5, tzinfo=UTC), 3)
    with pytest.raises(ValueError, match="strictly increasing"):
        enforce_splits([bars[1], bars[0], bars[2]], _windows(), Timeframe.H1)


def test_duplicate_open_time_excluded_and_flagged() -> None:
    first = _bar(datetime(2026, 1, 5, tzinfo=UTC))
    enforcement = enforce_splits([first, first], _windows(), Timeframe.H1)
    assert enforcement.duplicates == (first,)
    assert len(enforcement.in_window) == 1


def test_timeframe_step_monthly_refuses() -> None:
    with pytest.raises(ValueError, match="MN1"):
        timeframe_step(Timeframe.MN1)
    assert timeframe_step(Timeframe.H1) == timedelta(hours=1)
    assert timeframe_step(Timeframe.M15) == timedelta(minutes=15)
