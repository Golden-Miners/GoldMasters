"""Deterministic policy validation over normalized bars/quotes (pure).

Pipeline order per 02-RESEARCH.md §3: ordering (strictly increasing,
``bar_close_time == bar_open_time + 1h``) → duplicate (flag, keep first) →
gap (flag; weekend classification is plan 02-02 detail) → OHLC tick-align
only when a precision row exists, else skip → freshness (D-56 bar rule; the
quote rule uses the session-limit stub). ``now_utc`` is always an explicit
argument so every threshold is unit-testable without clock mocking.

A bar is healthy (``QualityStatus.OK``) only with zero flags; the retrieval
verdict (:func:`verdict_for_bars`) fails a batch whose worst condition is
stale or malformed, while gapped/duplicated batches stay servable with
flags — Schema §4 flags, never silent drops.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from goldmasters_contracts import MarketBar, MarketQuote, PrecisionTable, QualityStatus

__all__ = [
    "H1_SECONDS",
    "quote_stale_limit_for",
    "validate_bars",
    "validate_quote",
    "verdict_for_bars",
]

#: Seconds per H1 bar; boundary semantics beyond exact arithmetic defer to Phase 3.
H1_SECONDS = 3600

#: Worst-condition precedence: the batch status is the maximum by this order.
_SEVERITY: dict[QualityStatus, int] = {
    QualityStatus.OK: 0,
    QualityStatus.NOT_EVALUATED: 0,
    QualityStatus.DUPLICATE: 1,
    QualityStatus.GAP: 2,
    QualityStatus.STALE: 3,
    QualityStatus.UNSUPPORTED: 4,
    QualityStatus.MISSING_HISTORY: 5,
    QualityStatus.DISCONNECTED: 6,
    QualityStatus.MALFORMED: 7,
}

#: Batch verdicts that still serve (with flags) vs fail the retrieval.
_SERVABLE: frozenset[QualityStatus] = frozenset(
    {QualityStatus.OK, QualityStatus.DUPLICATE, QualityStatus.GAP}
)


def _worst(flags: Sequence[QualityStatus]) -> QualityStatus:
    """Worst flag by precedence, or ``OK`` when the bar is clean."""
    worst = QualityStatus.OK
    for flag in flags:
        if _SEVERITY[flag] > _SEVERITY[worst]:
            worst = flag
    return worst


def validate_bars(
    bars: Sequence[MarketBar],
    *,
    now_utc: datetime,
    stale_closed_bars: int = 2,
    stale_grace_seconds: int = 300,
    precision_table: PrecisionTable | None = None,
) -> list[MarketBar]:
    """Stamp quality onto normalized bars; duplicates beyond the first are dropped."""
    kept: list[MarketBar] = []
    flag_sets: list[list[QualityStatus]] = []
    first_index: dict[datetime, int] = {}
    previous_open: datetime | None = None

    for bar in bars:
        flags: list[QualityStatus] = []
        if bar.bar_open_time in first_index:
            # Duplicate: keep the first occurrence, flag it, drop this one.
            flag_sets[first_index[bar.bar_open_time]].append(QualityStatus.DUPLICATE)
            continue
        if previous_open is not None:
            if bar.bar_open_time < previous_open:
                flags.append(QualityStatus.MALFORMED)
            elif bar.bar_open_time > previous_open + timedelta(seconds=H1_SECONDS):
                flags.append(QualityStatus.GAP)
        if (
            bar.bar_close_time is None
            or (bar.bar_close_time - bar.bar_open_time).total_seconds() != H1_SECONDS
        ):
            flags.append(QualityStatus.MALFORMED)
        tick_flag = _tick_align_flag(bar, precision_table)
        if tick_flag is not None:
            flags.append(tick_flag)
        first_index[bar.bar_open_time] = len(kept)
        previous_open = bar.bar_open_time
        kept.append(bar)
        flag_sets.append(flags)

    stale = _bars_are_stale(kept, now_utc, stale_closed_bars, stale_grace_seconds)
    stamped: list[MarketBar] = []
    for bar, flags in zip(kept, flag_sets, strict=True):
        if stale and QualityStatus.STALE not in flags:
            flags = [*flags, QualityStatus.STALE]
        status = _worst(flags)
        stamped.append(bar.model_copy(update={"quality_status": status, "quality_flags": flags}))
    return stamped


def _tick_align_flag(
    bar: MarketBar, precision_table: PrecisionTable | None
) -> QualityStatus | None:
    """Misaligned OHLC vs the precision row → malformed; unknown precision → skip."""
    if precision_table is None:
        return None
    outcome = precision_table.lookup(bar.instrument_id, bar.provider_id, at=bar.retrieved_at)
    if outcome.status != "found" or outcome.row is None:
        return None
    tick = Decimal(outcome.row.tick_size)
    if tick <= 0:
        return None
    for price in (bar.open, bar.high, bar.low, bar.close):
        if price % tick != 0:
            return QualityStatus.MALFORMED
    return None


def _bars_are_stale(
    bars: Sequence[MarketBar], now_utc: datetime, closed_bars: int, grace_seconds: int
) -> bool:
    """D-56 bar rule: last *closed* bar older than ``2 × 1h + grace`` reads stale."""
    if not bars:
        return True
    last_close = bars[-1].bar_close_time
    if last_close is None:
        return True
    age = (now_utc.astimezone(UTC) - last_close.astimezone(UTC)).total_seconds()
    return age > closed_bars * H1_SECONDS + grace_seconds


def quote_stale_limit_for(
    moment_utc: datetime,
    *,
    overlap: int,
    major: int,
    asia: int,
    offhours: int,
) -> int:
    """Session-aware quote limit stub (02-RESEARCH.md §5; full table in plan 02-02).

    Windows are fixed UTC hours on a standard-time basis here; the configured
    per-session *limits* are already settings. Weekend/off-window moments fall
    through to the off-hours limit in this tracer.
    """
    moment = moment_utc.astimezone(UTC)
    minutes = moment.hour * 60 + moment.minute
    if 13 * 60 <= minutes < 16 * 60 + 30:
        return overlap
    if (8 * 60 <= minutes < 13 * 60) or (16 * 60 + 30 <= minutes < 21 * 60):
        return major
    if 0 <= minutes < 8 * 60:
        return asia
    return offhours


def validate_quote(quote: MarketQuote, *, now_utc: datetime, stale_seconds: int) -> MarketQuote:
    """Stamp quote freshness; a tick older than the session limit reads stale."""
    reference = quote.last_time or quote.ask_time or quote.bid_time or quote.retrieved_at
    age = (now_utc.astimezone(UTC) - reference.astimezone(UTC)).total_seconds()
    if age > stale_seconds:
        return quote.model_copy(
            update={"quality_status": QualityStatus.STALE, "quality_flags": [QualityStatus.STALE]}
        )
    return quote.model_copy(update={"quality_status": QualityStatus.OK, "quality_flags": []})


def verdict_for_bars(bars: Sequence[MarketBar]) -> QualityStatus | None:
    """Batch verdict: worst non-servable status, or ``None`` when servable.

    ``None`` means the batch may be served (healthy, gapped, or duplicated
    with flags); anything else names the failing condition for the C-09 map.
    """
    worst = QualityStatus.OK
    for bar in bars:
        if _SEVERITY[bar.quality_status] > _SEVERITY[worst]:
            worst = bar.quality_status
    if worst in _SERVABLE:
        return None
    return worst
