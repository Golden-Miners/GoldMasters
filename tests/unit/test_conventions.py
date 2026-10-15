"""Closed-bar conventions tracer (03-01 Task 1): one price, one adjacency, misorder.

Boundary tests (half-tick pin, both DST weekends, misorder evidence) arrive in
Task 2; this file proves the thin path end-to-end first.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from goldmasters_contracts import PrecisionRow, PrecisionTable, QualityStatus

from src.goldmasters.domain.conventions import (
    check_bar_order,
    quantize_for_instrument,
    utc_adjacent,
)

FIXTURE_T1 = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)
FIXTURE_T2 = datetime(2026, 1, 6, 16, 0, tzinfo=UTC)


def FIXTURE_table(tick_size: str = "0.01") -> PrecisionTable:  # noqa: N802
    row = PrecisionRow(
        instrument_id="xauusd",
        provider_id="mt5",
        tick_size=tick_size,
        decimals=2,
        provider_spec_version="build 4570",
        retrieved_at=FIXTURE_T1,
        valid_from=FIXTURE_T1,
    )
    return PrecisionTable().with_row(row)


def test_tracer_quantize_one_price_via_precision_table() -> None:
    assert quantize_for_instrument(
        Decimal("2387.105"),
        instrument_id="xauusd",
        provider_id="mt5",
        precision_table=FIXTURE_table(),
    ) == Decimal("2387.11")


def test_tracer_unknown_precision_skips_never_defaults() -> None:
    assert (
        quantize_for_instrument(
            Decimal("2387.105"),
            instrument_id="xauusd",
            provider_id="mt5",
            precision_table=PrecisionTable(),
        )
        is None
    )


def test_tracer_one_bar_pair_adjacent_in_utc() -> None:
    assert utc_adjacent(FIXTURE_T1, FIXTURE_T2, timeframe_seconds=3600) is True
    assert utc_adjacent(FIXTURE_T1, FIXTURE_T2, timeframe_seconds=7200) is False


def test_tracer_misordered_input_returns_malformed_and_preserves_order() -> None:
    opens = [FIXTURE_T2, FIXTURE_T1]
    assert check_bar_order(opens) == QualityStatus.MALFORMED
    assert opens == [FIXTURE_T2, FIXTURE_T1]  # never sorted
    assert check_bar_order([FIXTURE_T1, FIXTURE_T2]) is None
