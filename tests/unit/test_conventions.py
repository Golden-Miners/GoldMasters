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
    quantize_to_tick,
    server_wall_to_utc,
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


# --- Task 2 boundaries (D-3.2, D-3.5) -------------------------------------

FIXTURE_TICK = Decimal("0.01")
FIXTURE_SERVER_TZ = "America/New_York"  # DST transitions: 2026-03-08, 2026-11-01


def test_boundary_exact_half_tick_rounds_up() -> None:
    """D-3.2: a price exactly halfway between ticks pins ROUND_HALF_UP."""
    assert quantize_to_tick(Decimal("2387.105"), FIXTURE_TICK) == Decimal("2387.11")
    assert quantize_to_tick(Decimal("2387.115"), FIXTURE_TICK) == Decimal("2387.12")


def test_boundary_one_ulp_below_half_does_not_round_up() -> None:
    assert quantize_to_tick(Decimal("2387.104999999"), FIXTURE_TICK) == Decimal("2387.10")
    assert quantize_to_tick(Decimal("2387.10"), FIXTURE_TICK) == Decimal("2387.10")


def test_boundary_spring_forward_skipped_hour_adjacent_in_utc() -> None:
    """D-3.5: 02:00 never trades wall-side; the 01:00→03:00 wall gap is UTC-adjacent."""
    first = server_wall_to_utc(datetime(2026, 3, 8, 1, 0), FIXTURE_SERVER_TZ)
    second = server_wall_to_utc(datetime(2026, 3, 8, 3, 0), FIXTURE_SERVER_TZ)
    assert first == datetime(2026, 3, 8, 6, 0, tzinfo=UTC)
    assert second == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)
    assert utc_adjacent(first, second, timeframe_seconds=3600) is True


def test_boundary_fall_back_repeated_hour_needs_fold_clause() -> None:
    """D-3.5: 01:00 occurs twice; fold 0/1 selects the occurrence, chain stays adjacent."""
    midnight = server_wall_to_utc(datetime(2026, 11, 1, 0, 0), FIXTURE_SERVER_TZ)
    first_one = server_wall_to_utc(datetime(2026, 11, 1, 1, 0), FIXTURE_SERVER_TZ, fold=0)
    second_one = server_wall_to_utc(datetime(2026, 11, 1, 1, 0), FIXTURE_SERVER_TZ, fold=1)
    two = server_wall_to_utc(datetime(2026, 11, 1, 2, 0), FIXTURE_SERVER_TZ)
    assert (midnight, first_one, second_one, two) == (
        datetime(2026, 11, 1, 4, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 5, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 6, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 7, 0, tzinfo=UTC),
    )
    for earlier, later in ((midnight, first_one), (first_one, second_one), (second_one, two)):
        assert utc_adjacent(earlier, later, timeframe_seconds=3600) is True


def test_boundary_misorder_evidence_and_no_silent_sort() -> None:
    """D-3.5: MALFORMED is returned; the implementation never calls sorted( on bars."""
    import pathlib

    opens = [FIXTURE_T1, FIXTURE_T2, FIXTURE_T1]
    assert check_bar_order(opens) == QualityStatus.MALFORMED
    assert opens == [FIXTURE_T1, FIXTURE_T2, FIXTURE_T1]
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "goldmasters"
        / "domain"
        / "conventions.py"
    ).read_text(encoding="utf-8")
    assert "sorted(" not in source


def test_boundary_fail_closed_on_naive_and_non_decimal() -> None:
    import pytest

    with pytest.raises(ValueError, match="timezone-aware"):
        utc_adjacent(FIXTURE_T1, datetime(2026, 1, 6, 16, 0), timeframe_seconds=3600)
    with pytest.raises(ValueError, match="naive"):
        server_wall_to_utc(FIXTURE_T1, FIXTURE_SERVER_TZ)
    with pytest.raises(ValueError, match="fold"):
        server_wall_to_utc(datetime(2026, 11, 1, 1, 0), FIXTURE_SERVER_TZ, fold=2)
    with pytest.raises(TypeError, match="Decimal"):
        quantize_to_tick(2387.105, FIXTURE_TICK)  # type: ignore[arg-type]


def test_boundary_deterministic_repeat_runs_identical() -> None:
    """Every case uses explicit arguments; repeat calls return identical values."""
    for _ in range(2):
        assert quantize_to_tick(Decimal("2387.105"), FIXTURE_TICK) == Decimal("2387.11")
        assert utc_adjacent(FIXTURE_T1, FIXTURE_T2, timeframe_seconds=3600) is True
        assert check_bar_order([FIXTURE_T2, FIXTURE_T1]) == QualityStatus.MALFORMED
