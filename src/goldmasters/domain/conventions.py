"""Closed-bar conventions: tick quantization, UTC adjacency, order check (D-3.2/D-3.5).

Pure functions on :class:`~decimal.Decimal` and UTC instants with explicit
arguments — no wall-clock reads, no module-global config, no mutation
(``validation.py`` precedent). Tick context arrives via
``PrecisionTable.lookup``; unknown precision means the caller skips
tick-alignment, never a default tick (Phase-2 precedent).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from goldmasters_contracts import PrecisionTable, QualityStatus

__all__ = [
    "check_bar_order",
    "quantize_for_instrument",
    "quantize_to_tick",
    "server_wall_to_utc",
    "utc_adjacent",
]


def quantize_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    """Snap ``price`` to the tick grid, exact-half-ticks away from banker's (D-3.2).

    The single locked mode is ``decimal.ROUND_HALF_UP``: a price exactly
    halfway between ticks rounds up; anything below the half stays down.
    """
    if not isinstance(price, Decimal) or not isinstance(tick_size, Decimal):
        raise TypeError("price and tick_size must be Decimal (Decimal-only price path)")
    if tick_size <= 0:
        raise ValueError(f"tick_size must be positive, got {tick_size}")
    steps = (price / tick_size).to_integral_value(rounding=ROUND_HALF_UP)
    return steps * tick_size


def quantize_for_instrument(
    price: Decimal,
    *,
    instrument_id: str,
    provider_id: str,
    precision_table: PrecisionTable,
    at: datetime | None = None,
) -> Decimal | None:
    """Quantize via the precision-table tick; ``None`` (skip) when unknown.

    The table answers ``unknown`` for a missing key or an out-of-interval
    lookup — that stays a skip, never a default tick.
    """
    outcome = precision_table.lookup(instrument_id, provider_id, at=at)
    if outcome.status != "found" or outcome.row is None:
        return None
    return quantize_to_tick(price, Decimal(outcome.row.tick_size))


def utc_adjacent(open_a: datetime, open_b: datetime, *, timeframe_seconds: int) -> bool:
    """True when two bar opens are exactly one timeframe apart in UTC (D-3.5).

    The comparison is on UTC instants, where DST has no effect — a server-wall
    gap of two hours across spring-forward still reads adjacent here.
    """
    if timeframe_seconds <= 0:
        raise ValueError(f"timeframe_seconds must be positive, got {timeframe_seconds}")
    for instant in (open_a, open_b):
        if instant.tzinfo is None or instant.tzinfo.utcoffset(instant) is None:
            raise ValueError("bar opens must be timezone-aware")
    delta = open_b.astimezone(UTC) - open_a.astimezone(UTC)
    return delta == timedelta(seconds=timeframe_seconds)


def server_wall_to_utc(wall_open: datetime, server_timezone: str, *, fold: int = 0) -> datetime:
    """Attach the server zone to a naive wall reading, then convert to UTC.

    ``fold`` selects the occurrence of the ambiguous hour at fall-back
    (``0`` first, ``1`` second — the server-local fold clause of D-3.5).
    Spring-forward's skipped hour never occurs wall-side, so no clause is
    needed there; :func:`utc_adjacent` stays canonical regardless.
    """
    if wall_open.tzinfo is not None:
        raise ValueError("wall_open must be naive (a server-wall reading)")
    if fold not in (0, 1):
        raise ValueError(f"fold must be 0 or 1 (the ambiguous-hour occurrence), got {fold}")
    return wall_open.replace(tzinfo=ZoneInfo(server_timezone), fold=fold).astimezone(UTC)


def check_bar_order(bar_open_times: Sequence[datetime]) -> QualityStatus | None:
    """``MALFORMED`` on the first backward step, never a silent sort (D-3.5).

    Mirrors the ``validation.py`` misorder precedent
    (``bar_open_time < previous_open``); duplicates are validation's concern,
    not reordering evidence. A misordered analysis input surfaces as
    ``INSUFFICIENT_DATA`` downstream — the input order is preserved untouched.
    """
    previous: datetime | None = None
    for open_time in bar_open_times:
        if previous is not None and open_time < previous:
            return QualityStatus.MALFORMED
        previous = open_time
    return None
