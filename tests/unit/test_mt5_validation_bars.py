"""Bar validation policy tests (02-02 Task 1: D-56; research §3 steps 1-7).

Labelled fixtures (``FIXTURE_`` prefix, tests-only) over synthetic H1 bars —
never live data. Every threshold carries a ±1s boundary pair.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from goldmasters_contracts import (
    MarketBar,
    PrecisionRow,
    PrecisionTable,
    QualityStatus,
    Timeframe,
    VolumeType,
)

from services.mt5_adapter.normalize import NormalizationError, normalize_bars
from services.mt5_adapter.validation import validate_bars

#: Tuesday 2026-01-06 — mid-week, far from any closed window.
FIXTURE_TUESDAY = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)

WEEKEND_SPEC = "Fri 21:00-Sun 22:00"
BREAK_SPEC = "21:00-22:00"


def FIXTURE_bar(  # noqa: N802 - fixture prefix is the labelling convention
    open_time: datetime,
    *,
    o: str = "2381.00",
    h: str = "2383.00",
    lo: str = "2380.00",
    c: str = "2382.00",
) -> MarketBar:
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=open_time,
        bar_close_time=open_time + timedelta(hours=1),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
        volume=Decimal(100),
        volume_type=VolumeType.TICK,
        retrieved_at=open_time + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.NOT_EVALUATED,
    )


def FIXTURE_sequence(  # noqa: N802
    start: datetime, count: int
) -> list[MarketBar]:
    return [FIXTURE_bar(start + timedelta(hours=i)) for i in range(count)]


def _stamped(bars: list[MarketBar], now: datetime, **kwargs: Any) -> list[MarketBar]:
    return validate_bars(
        bars,
        now_utc=now,
        stale_closed_bars=2,
        stale_grace_seconds=300,
        weekend_spec=WEEKEND_SPEC,
        break_spec=BREAK_SPEC,
        **kwargs,
    )


def test_strictly_increasing_exact_sequence_is_ok() -> None:
    bars = FIXTURE_sequence(FIXTURE_TUESDAY, 4)
    now = FIXTURE_TUESDAY + timedelta(hours=4, minutes=30)
    stamped = _stamped(bars, now)
    assert all(b.quality_status == QualityStatus.OK for b in stamped)
    assert all(b.quality_flags == [] for b in stamped)


def test_non_increasing_bar_is_malformed_never_reordered() -> None:
    bars = FIXTURE_sequence(FIXTURE_TUESDAY, 3)
    bars[1], bars[2] = bars[2], bars[1]
    stamped = _stamped(bars, FIXTURE_TUESDAY + timedelta(hours=4))
    assert any(b.quality_status == QualityStatus.MALFORMED for b in stamped)
    # Order preserved — validation flags, never re-sorts.
    assert [b.bar_open_time for b in stamped] == [b.bar_open_time for b in bars]


def test_misaligned_close_is_malformed() -> None:
    bar = FIXTURE_bar(FIXTURE_TUESDAY).model_copy(
        update={"bar_close_time": FIXTURE_TUESDAY + timedelta(minutes=30)}
    )
    stamped = _stamped([bar], FIXTURE_TUESDAY + timedelta(hours=2))
    assert stamped[0].quality_status == QualityStatus.MALFORMED


def test_duplicate_keeps_first_flags_it_drops_second() -> None:
    bars = [*FIXTURE_sequence(FIXTURE_TUESDAY, 2), FIXTURE_bar(FIXTURE_TUESDAY)]
    stamped = _stamped(bars, FIXTURE_TUESDAY + timedelta(hours=3))
    assert len(stamped) == 2
    assert QualityStatus.DUPLICATE in stamped[0].quality_flags


def test_midweek_gap_is_missing_history() -> None:
    bars = [FIXTURE_bar(FIXTURE_TUESDAY), FIXTURE_bar(FIXTURE_TUESDAY + timedelta(hours=2))]
    stamped = _stamped(bars, FIXTURE_TUESDAY + timedelta(hours=3))
    assert stamped[1].quality_status == QualityStatus.MISSING_HISTORY
    assert QualityStatus.MISSING_HISTORY in stamped[1].quality_flags


def test_tick_align_flags_malformed_only_with_precision_row() -> None:
    bars = FIXTURE_sequence(FIXTURE_TUESDAY, 2)
    now = FIXTURE_TUESDAY + timedelta(hours=3)
    assert all(b.quality_status == QualityStatus.OK for b in _stamped(bars, now))
    row = PrecisionRow(
        instrument_id="xauusd",
        provider_id="mt5",
        tick_size="0.30",
        decimals=2,
        provider_spec_version="build 4570",
        retrieved_at=now,
        valid_from=FIXTURE_TUESDAY,
    )
    table = PrecisionTable().with_row(row)
    stamped = _stamped(bars, now, precision_table=table)
    assert any(b.quality_status == QualityStatus.MALFORMED for b in stamped)


def test_zero_row_precision_skips_alignment() -> None:
    bars = FIXTURE_sequence(FIXTURE_TUESDAY, 2)
    stamped = _stamped(bars, FIXTURE_TUESDAY + timedelta(hours=3), precision_table=PrecisionTable())
    assert all(b.quality_status == QualityStatus.OK for b in stamped)


def test_volume_semantics_preserved() -> None:
    rows = [
        {
            "time": int((FIXTURE_TUESDAY + timedelta(hours=i)).timestamp()),
            "open": 2381.0,
            "high": 2383.0,
            "low": 2380.0,
            "close": 2382.0,
            "tick_volume": tick,
            "spread": 35,
            "real_volume": 999,
        }
        for i, tick in enumerate((100, 0, None))
    ]
    forming = {
        "time": int((FIXTURE_TUESDAY + timedelta(hours=3)).timestamp()),
        "open": 2381.0,
        "high": 2383.0,
        "low": 2380.0,
        "close": 2382.0,
        "tick_volume": 1,
        "spread": 35,
        "real_volume": 0,
    }
    bars = normalize_bars(
        [forming, *reversed(rows)],
        instrument_id="xauusd",
        provider_symbol="XAUUSD",
        timeframe="H1",
        server_timezone="UTC",
        retrieved_at=FIXTURE_TUESDAY + timedelta(hours=3),
    )
    assert bars[0].volume == Decimal(100) and bars[0].volume_type == VolumeType.TICK
    assert bars[1].volume is None
    assert bars[1].volume_type == VolumeType.NOT_AVAILABLE
    assert bars[2].volume is None


@pytest.mark.parametrize("delta_seconds", [-1, 1])
def test_freshness_boundary_pm1s(delta_seconds: int) -> None:
    """Fresh at exactly (2h + grace - 1s); stale at (2h + grace + 1s)."""
    bars = FIXTURE_sequence(FIXTURE_TUESDAY, 2)
    last_close = FIXTURE_TUESDAY + timedelta(hours=2)
    now = last_close + timedelta(hours=2, seconds=300 + delta_seconds)
    stamped = _stamped(bars, now)
    if delta_seconds < 0:
        assert all(b.quality_status == QualityStatus.OK for b in stamped)
    else:
        assert all(b.quality_status == QualityStatus.STALE for b in stamped)
        assert all(QualityStatus.STALE in b.quality_flags for b in stamped)


def test_nan_inf_rejected_before_construction() -> None:
    row = {
        "time": int(FIXTURE_TUESDAY.timestamp()),
        "open": float("nan"),
        "high": 2383.0,
        "low": 2380.0,
        "close": 2382.0,
        "tick_volume": 100,
        "spread": 35,
        "real_volume": 0,
    }
    with pytest.raises(NormalizationError):
        normalize_bars(
            [row, row],
            instrument_id="xauusd",
            provider_symbol="XAUUSD",
            timeframe="H1",
            server_timezone="UTC",
            retrieved_at=FIXTURE_TUESDAY,
        )
