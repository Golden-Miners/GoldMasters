"""Shared Decimal indicator math reused by more than one strategy agent (D-3.1).

Pure :class:`~decimal.Decimal` functions over closed
:class:`~goldmasters_contracts.MarketBar` bars with explicit parameters — no
literals (windows arrive as arguments), no wall-clock reads, no
module-global config, no mutation. Swing/engagement helpers are reused from
:mod:`domain.structure` as-is, never re-implemented here.

Every function reads only the bars it is given, so callers pass the prefix
they may read and full-series indicators cannot leak future bars into
earlier indexes. Too few bars yields ``None`` (insufficient_data, never a
default); malformed inputs raise. Mirrors the ``quantize_for_instrument``
None-skip precedent and the ``_checked_window`` positive-int precedent in
``domain/structure.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from goldmasters_contracts import MarketBar

__all__ = [
    "average_gain",
    "average_loss",
    "average_true_range",
    "ema_close",
]


def _checked_bars(bars: Sequence[MarketBar]) -> list[MarketBar]:
    """Malformed input raises; an empty sequence is malformed, not a policy."""
    ordered = list(bars)
    if not ordered:
        raise ValueError("at least one closed bar is required")
    for bar in ordered:
        if not isinstance(bar, MarketBar):
            raise TypeError("bars must be MarketBar (malformed input raises)")
    return ordered


def _checked_period(period: int) -> None:
    """Fail closed on a non-positive lookback (structure._checked_window precedent)."""
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError(f"period must be a positive int, got {period!r}")


def _true_ranges(bars: list[MarketBar]) -> list[Decimal]:
    """Per-bar true range from the second bar on (needs a previous close)."""
    ranges: list[Decimal] = []
    for previous, bar in zip(bars, bars[1:]):
        high_low = bar.high - bar.low
        high_prev = abs(bar.high - previous.close)
        low_prev = abs(bar.low - previous.close)
        ranges.append(max(high_low, high_prev, low_prev))
    return ranges


def average_true_range(bars: Sequence[MarketBar], *, period: int) -> Decimal | None:
    """Decimal mean of the last ``period`` true ranges; ``None`` when short.

    Needs ``period + 1`` bars (each true range consumes a previous close).
    """
    ordered = _checked_bars(bars)
    _checked_period(period)
    ranges = _true_ranges(ordered)
    if len(ranges) < period:
        return None
    window = ranges[len(ranges) - period :]
    return sum(window, Decimal(0)) / Decimal(period)


def ema_close(bars: Sequence[MarketBar], *, period: int) -> Decimal | None:
    """Exponential moving average of closes; ``None`` when short.

    Seeded with the simple mean of the first ``period`` closes, then
    smoothed with ``k = 2 / (period + 1)`` over the remaining given bars
    only — pass the prefix under evaluation, never the full series.
    """
    ordered = _checked_bars(bars)
    _checked_period(period)
    if len(ordered) < period:
        return None
    closes = [bar.close for bar in ordered]
    average = sum(closes[:period], Decimal(0)) / Decimal(period)
    factor = Decimal(2) / (Decimal(period) + Decimal(1))
    for close in closes[period:]:
        average = close * factor + average * (Decimal(1) - factor)
    return average


def _close_changes(bars: list[MarketBar]) -> list[Decimal]:
    """Close-to-close moves from the second bar on."""
    return [bar.close - previous.close for previous, bar in zip(bars, bars[1:])]


def average_gain(bars: Sequence[MarketBar], *, period: int) -> Decimal | None:
    """Decimal mean of upward close moves over the last ``period``; ``None`` when short.

    Needs ``period + 1`` bars. Downward moves contribute zero (gain leg of
    RSI-style gain/loss means); the loss leg lives in :func:`average_loss`.
    """
    ordered = _checked_bars(bars)
    _checked_period(period)
    changes = _close_changes(ordered)
    if len(changes) < period:
        return None
    window = changes[len(changes) - period :]
    upward = [change if change > 0 else Decimal(0) for change in window]
    return sum(upward, Decimal(0)) / Decimal(period)


def average_loss(bars: Sequence[MarketBar], *, period: int) -> Decimal | None:
    """Decimal mean of downward close moves (as positive magnitudes); ``None`` when short.

    Mirror of :func:`average_gain`: upward moves contribute zero, downward
    moves contribute their magnitude.
    """
    ordered = _checked_bars(bars)
    _checked_period(period)
    changes = _close_changes(ordered)
    if len(changes) < period:
        return None
    window = changes[len(changes) - period :]
    downward = [-change if change < 0 else Decimal(0) for change in window]
    return sum(downward, Decimal(0)) / Decimal(period)
