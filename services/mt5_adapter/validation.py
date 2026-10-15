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
    "classify_gap",
    "is_weekend_closed",
    "missing_opens",
    "parse_daily_window",
    "parse_session_windows",
    "parse_weekend_window",
    "quote_stale_limit_for",
    "session_for",
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
    weekend_spec: str | None = None,
    break_spec: str | None = None,
    preserve: dict[datetime, Sequence[QualityStatus]] | None = None,
) -> list[MarketBar]:
    """Stamp quality onto normalized bars; duplicates beyond the first are dropped.

    A detected gap is classified per D-58: an expected (weekend/break-adjacent)
    gap flags ``GAP`` on the later bar; any other gap stamps ``MISSING_HISTORY``
    on it. Without specs every gap stays a plain ``GAP`` flag (tracer behavior).

    ``preserve`` carries first-pass flags across a backfill merge: bars already
    seen keep their ``MALFORMED``/``DUPLICATE`` evidence while gap, staleness
    and history verdicts are recomputed on the merged sequence — a refill must
    fill absence, never launder misordering evidence.
    """
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
                missing = missing_opens(previous_open, bar.bar_open_time)
                if (
                    weekend_spec is not None
                    and classify_gap(missing, weekend_spec=weekend_spec, break_spec=break_spec)
                    == "missing-history"
                ):
                    flags.append(QualityStatus.MISSING_HISTORY)
                else:
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
        if preserve is not None and bar.bar_open_time in preserve:
            kept_evidence = [
                flag
                for flag in preserve[bar.bar_open_time]
                if flag in (QualityStatus.MALFORMED, QualityStatus.DUPLICATE)
            ]
            recomputed = [
                flag
                for flag in flags
                if flag not in (QualityStatus.MALFORMED, QualityStatus.DUPLICATE)
            ]
            flags = [*kept_evidence, *recomputed]
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
    overlap_windows: str = "13:00-16:30",
    major_windows: str = "08:00-13:00,16:30-21:00",
    asia_windows: str = "00:00-08:00",
) -> int:
    """Session-aware quote limit (02-RESEARCH.md §3; windows settings-driven).

    Windows default to the research table on a standard-time basis; the
    operator retunes them via ``GOLDMASTERS_SESSION_*`` without code change
    (DST ±1h is operator-confirmed per D-57).
    """
    session = session_for(
        moment_utc,
        overlap_windows=overlap_windows,
        major_windows=major_windows,
        asia_windows=asia_windows,
    )
    limits = {"overlap": overlap, "major": major, "asia": asia}
    return limits[session] if session in limits else offhours


def validate_quote(
    quote: MarketQuote,
    *,
    now_utc: datetime,
    stale_seconds: int,
    weekend_spec: str | None = None,
) -> MarketQuote:
    """Stamp quote freshness; a tick older than the session limit reads stale.

    Inside the weekend-closed window the tick reads disconnected (unavailable),
    never stale, regardless of age (D-57/D-58). Without a spec the tracer
    threshold behavior applies unchanged.
    """
    if weekend_spec is not None and is_weekend_closed(now_utc, weekend_spec):
        return quote.model_copy(
            update={
                "quality_status": QualityStatus.DISCONNECTED,
                "quality_flags": [QualityStatus.DISCONNECTED],
            }
        )
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


def missing_opens(previous_open: datetime, bar_open: datetime) -> list[datetime]:
    """Hour opens strictly between two consecutive kept bars (the absent span)."""
    missing: list[datetime] = []
    cursor = previous_open + timedelta(seconds=H1_SECONDS)
    while cursor < bar_open:
        missing.append(cursor)
        cursor += timedelta(seconds=H1_SECONDS)
    return missing


def _parse_hhmm(token: str) -> int:
    """Parse ``HH:MM`` to minutes since midnight; raises ``ValueError`` when malformed."""
    parts = token.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"expected HH:MM, got {token!r}")
    hour, minute = int(parts[0]), int(parts[1])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"hour/minute out of range in {token!r}")
    return hour * 60 + minute


def parse_session_windows(spec: str) -> list[tuple[int, int]]:
    """Parse a daily window spec like ``"08:00-13:00,16:30-21:00"`` (fail-closed)."""
    windows: list[tuple[int, int]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            start_raw, end_raw = chunk.split("-")
            start, end = _parse_hhmm(start_raw), _parse_hhmm(end_raw)
        except ValueError as exc:
            raise ValueError(f"malformed session window {chunk!r} in {spec!r}") from exc
        if end <= start:
            raise ValueError(f"window end must follow start in {chunk!r}")
        windows.append((start, end))
    if not windows:
        raise ValueError(f"no windows parsed from {spec!r}")
    return windows


def parse_daily_window(spec: str) -> tuple[int, int]:
    """Parse a single daily window like ``"21:00-22:00"`` (fail-closed)."""
    windows = parse_session_windows(spec)
    if len(windows) != 1:
        raise ValueError(f"expected exactly one window in {spec!r}")
    return windows[0]


_DOW: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def parse_weekend_window(spec: str) -> tuple[int, int]:
    """Parse ``"Fri 21:00-Sun 22:00"`` to weekly-minute bounds (fail-closed)."""
    try:
        start_raw, end_raw = spec.split("-")
        start_dow_raw, start_hm = start_raw.strip().split()
        end_dow_raw, end_hm = end_raw.strip().split()
        start = _DOW[start_dow_raw.strip().lower()] * 1440 + _parse_hhmm(start_hm)
        end = _DOW[end_dow_raw.strip().lower()] * 1440 + _parse_hhmm(end_hm)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"malformed weekend window {spec!r}") from exc
    if end <= start:
        raise ValueError(f"weekend window end must follow start in {spec!r}")
    return (start, end)


def _weekly_minutes(moment_utc: datetime) -> int:
    moment = moment_utc.astimezone(UTC)
    return moment.weekday() * 1440 + moment.hour * 60 + moment.minute


def is_weekend_closed(moment_utc: datetime, weekend_spec: str) -> bool:
    """True inside the configured weekend-closed window (D-58)."""
    start, end = parse_weekend_window(weekend_spec)
    return start <= _weekly_minutes(moment_utc) < end


def session_for(
    moment_utc: datetime,
    *,
    overlap_windows: str = "13:00-16:30",
    major_windows: str = "08:00-13:00,16:30-21:00",
    asia_windows: str = "00:00-08:00",
) -> str:
    """Session name for a UTC moment: overlap > major > Asia > off-hours."""
    moment = moment_utc.astimezone(UTC)
    minutes = moment.hour * 60 + moment.minute
    if any(start <= minutes < end for start, end in parse_session_windows(overlap_windows)):
        return "overlap"
    if any(start <= minutes < end for start, end in parse_session_windows(major_windows)):
        return "major"
    if any(start <= minutes < end for start, end in parse_session_windows(asia_windows)):
        return "asia"
    return "offhours"


def classify_gap(
    missing_opens: Sequence[datetime], *, weekend_spec: str, break_spec: str | None = None
) -> str:
    """D-58 classifier: ``"expected"`` vs ``"missing-history"`` (never synthesis).

    Every missing hour-open inside the weekend window → expected. A single-bar
    gap adjacent to the daily-break window → expected (tolerated). Anything
    else → missing-history.
    """
    if not missing_opens:
        return "expected"
    if all(is_weekend_closed(open_time, weekend_spec) for open_time in missing_opens):
        return "expected"
    if break_spec is not None and len(missing_opens) == 1:
        start, end = parse_daily_window(break_spec)
        moment = missing_opens[0].astimezone(UTC)
        minutes = moment.hour * 60 + moment.minute
        # Adjacent means the missing hour touches the break window either side.
        if start - 60 <= minutes < end + 60:
            return "expected"
    return "missing-history"
