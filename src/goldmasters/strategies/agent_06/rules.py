"""Agent 6 rule composition: session range first, completed-range breakout second.

A confirmed break of the predefined session range may capture a directional
move — so the range is formed from in-session candles only (single local
session day in the named timezone), the breakout needs buffer plus a second
confirming close, and stale breakouts expire. Missing numerics yield
``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfoNotFoundError

from goldmasters_contracts import (
    Direction,
    MarketBar,
    QualityStatus,
    Timeframe,
    TrendRegime,
)

from src.goldmasters.domain.conventions import session_local_date
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent06Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    session_name: str | None
    session_tz: str | None
    range_minutes: int | None
    buffer_ticks: int | None
    expiry_minutes: int | None
    max_spread_ticks: int | None


def _check(
    rule_id: str, verdict: str, evidence: str, reason: str, inputs: dict[str, str]
) -> RuleCheck:
    return RuleCheck(
        rule_id=rule_id,
        verdict=verdict,  # type: ignore[arg-type]
        inputs=inputs,
        evidence=evidence,
        reason=reason,
    )


def bar_step_minutes(bars: Sequence[MarketBar]) -> Decimal | None:
    """Median open-to-open gap in minutes; ``None`` when undeterminable.

    Derived from the bars under evaluation (never an assumed bar length), so
    the range-minute window converts to a bar count without inventing a
    timeframe duration.
    """
    ordered = list(bars)
    if len(ordered) < 2:
        return None
    gaps = [
        (later.bar_open_time - earlier.bar_open_time).total_seconds() / 60
        for earlier, later in zip(ordered, ordered[1:], strict=False)
    ]
    positive = sorted(gap for gap in gaps if gap > 0)
    if not positive:
        return None
    middle = len(positive) // 2
    if len(positive) % 2 == 1:
        return Decimal(str(positive[middle]))
    return Decimal(str((positive[middle - 1] + positive[middle]) / 2))


def range_bar_count(bars: Sequence[MarketBar], params: Agent06Params) -> int | None:
    """Leading bars forming the session range; ``None`` when unconfigured.

    A structural minimum of two bars (a range needs a high and a low) applies;
    anything smaller than the minute window still fails closed through the
    breakout math, never through a default window.
    """
    if params.range_minutes is None:
        return None
    step = bar_step_minutes(bars)
    if step is None or step <= 0:
        return None
    return max(2, int(Decimal(params.range_minutes) // step))


def range_bounds(bars: Sequence[MarketBar], count: int) -> tuple[Decimal, Decimal]:
    """Range high/low over the first ``count`` in-session bars."""
    window = list(bars)[:count]
    return max(bar.high for bar in window), min(bar.low for bar in window)


def rule_session_scope(bars: Sequence[MarketBar], params: Agent06Params) -> RuleCheck:
    """Named session in its timezone; every bar must share one local day.

    The zoneinfo database converts each UTC instant, so DST shifts never
    misplace a bar (server-time correctness); a session spanning midnight
    reads as expired data, never as a wider range.
    """
    if params.session_name is None or params.session_tz is None:
        return _check(
            "session-scope",
            "unknown",
            "unconfigured session name or timezone",
            "fail-closed: session_name/session_tz unset",
            {},
        )
    try:
        days = {session_local_date(bar.bar_open_time, params.session_tz) for bar in bars}
    except ZoneInfoNotFoundError:
        return _check(
            "session-scope",
            "unknown",
            f"session timezone {params.session_tz!r} names no IANA zone",
            "fail-closed: session_tz names no timezone",
            {},
        )
    if len(days) > 1:
        return _check(
            "session-scope",
            "fail",
            f"bars span {len(days)} local session days: session-end expiry",
            "opening range: stale session data, not one session range",
            {"session": params.session_name, "tz": params.session_tz},
        )
    return _check(
        "session-scope",
        "pass",
        f"all bars in session {params.session_name} day {days.pop()}",
        "opening range: single-session range only",
        {"session": params.session_name, "tz": params.session_tz},
    )


def rule_range_breakout(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent06Params
) -> tuple[RuleCheck, Direction | None, Decimal | None, Decimal | None]:
    """Completed-range breakout beyond range edge plus buffer.

    The buffer rides ``buffer_ticks`` times the context tick size (derived
    distance, never a price literal); a close inside edge-plus-buffer is chop,
    not a break. Returns the range bounds for confirmation and stops.
    """
    if params.range_minutes is None or params.buffer_ticks is None:
        return (
            _check(
                "range-breakout",
                "unknown",
                "unconfigured range window or buffer",
                "fail-closed: range_minutes/buffer_ticks unset",
                {},
            ),
            None,
            None,
            None,
        )
    if ctx.tick_size is None:
        return (
            _check(
                "range-breakout",
                "unknown",
                "buffer indeterminate without tick size",
                "buffer distance needs the context tick size",
                {},
            ),
            None,
            None,
            None,
        )
    count = range_bar_count(bars, params)
    ordered = list(bars)
    if count is None or len(ordered) <= count:
        return (
            _check(
                "range-breakout",
                "unknown",
                "range window exceeds the bars under evaluation",
                "range formation needs a bar beyond the range",
                {},
            ),
            None,
            None,
            None,
        )
    high, low = range_bounds(ordered, count)
    buffer = Decimal(params.buffer_ticks) * Decimal(ctx.tick_size)
    close = ordered[-1].close
    inputs = {"range_high": str(high), "range_low": str(low), "buffer": str(buffer)}
    if close > high + buffer:
        return (
            _check(
                "range-breakout",
                "pass",
                f"close {close} breaks range high {high} plus buffer {buffer}",
                "opening range: confirmed upside break",
                inputs,
            ),
            Direction.LONG,
            high,
            low,
        )
    if close < low - buffer:
        return (
            _check(
                "range-breakout",
                "pass",
                f"close {close} breaks range low {low} minus buffer {buffer}",
                "opening range: confirmed downside break",
                inputs,
            ),
            Direction.SHORT,
            high,
            low,
        )
    return (
        _check(
            "range-breakout",
            "fail",
            f"close {close} inside {low} minus buffer to {high} plus buffer",
            "opening range: no completed-range breakout",
            inputs,
        ),
        None,
        None,
        None,
    )


def rule_entry_confirmation(
    bars: Sequence[MarketBar],
    ctx: MarketContext,
    params: Agent06Params,
    direction: Direction | None,
    range_high: Decimal | None,
    range_low: Decimal | None,
) -> RuleCheck:
    """Confirmation: the prior close already held beyond the broken edge.

    A breakout close with the prior close back inside the range is a failed
    break (bull/bear trap), never a setup — the operator's failure handling.
    """
    if params.buffer_ticks is None or direction is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "confirmation indeterminate without buffer and direction",
            "fail-closed: buffer_ticks unset or no breakout direction",
            {},
        )
    if ctx.tick_size is None or range_high is None or range_low is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "confirmation indeterminate without range bounds",
            "no range bounds from the breakout rule",
            {},
        )
    ordered = list(bars)
    buffer = Decimal(params.buffer_ticks) * Decimal(ctx.tick_size)
    prior = ordered[-2].close
    if direction == Direction.LONG:
        held = prior > range_high + buffer
        level = range_high + buffer
    else:
        held = prior < range_low - buffer
        level = range_low - buffer
    inputs = {"prior_close": str(prior), "level": str(level)}
    if held:
        return _check(
            "entry-confirmation",
            "pass",
            f"prior close {prior} already beyond {level}: confirmed break",
            "opening range: breakout with confirmation",
            inputs,
        )
    return _check(
        "entry-confirmation",
        "fail",
        f"prior close {prior} back inside {level}: failed breakout",
        "opening range: breakout not confirmed",
        inputs,
    )


def rule_breakout_expiry(
    bars: Sequence[MarketBar], params: Agent06Params, count: int | None
) -> RuleCheck:
    """The range completion must sit inside the expiry window (session-end expiry)."""
    if params.expiry_minutes is None or count is None:
        return _check(
            "breakout-expiry",
            "unknown",
            "unconfigured expiry window",
            "fail-closed: expiry_minutes unset or no range window",
            {},
        )
    ordered = list(bars)
    elapsed = (ordered[-1].bar_close_time - ordered[count - 1].bar_close_time).total_seconds() / 60
    inputs = {"elapsed_minutes": str(elapsed), "expiry_minutes": str(params.expiry_minutes)}
    if elapsed <= params.expiry_minutes:
        return _check(
            "breakout-expiry",
            "pass",
            f"breakout {elapsed} minutes after range completion, inside {params.expiry_minutes}",
            "opening range: breakout not expired",
            inputs,
        )
    return _check(
        "breakout-expiry",
        "fail",
        f"breakout {elapsed} minutes after range completion, past {params.expiry_minutes}",
        "opening range: stale breakout, session moved on",
        inputs,
    )


def rule_session_quality(ctx: MarketContext, params: Agent06Params) -> RuleCheck:
    """Spread/session filter: configured spread cap with clean quality only.

    Bars carry no spread series, so the filter reads the quality channel —
    any unreliable-candle flag (gap, stale, disconnected) rejects, since a
    spread cap cannot be proven on unreliable prints.
    """
    if params.max_spread_ticks is None:
        return _check(
            "session-quality",
            "unknown",
            "unconfigured spread cap",
            "fail-closed: max_spread_ticks unset",
            {},
        )
    if ctx.quality_status == QualityStatus.OK and not ctx.quality_flags:
        return _check(
            "session-quality",
            "pass",
            "quality clean: no unreliable-candle flags against the spread cap",
            "opening range: spread/session filter satisfied",
            {"max_spread_ticks": str(params.max_spread_ticks)},
        )
    return _check(
        "session-quality",
        "fail",
        f"quality {ctx.quality_status.value} with flags {[f.value for f in ctx.quality_flags]}",
        "opening range: unreliable candles, spread cap unprovable",
        {"max_spread_ticks": str(params.max_spread_ticks)},
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent06Params
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the five operator rules; stop is the unbroken range extreme."""
    ordered = list(bars)
    scope = rule_session_scope(ordered, params)
    breakout, direction, high, low = rule_range_breakout(ordered, ctx, params)
    confirmation = rule_entry_confirmation(ordered, ctx, params, direction, high, low)
    count = range_bar_count(ordered, params)
    expiry = rule_breakout_expiry(ordered, params, count)
    quality = rule_session_quality(ctx, params)
    checks = [scope, breakout, confirmation, expiry, quality]
    if direction is None or high is None or low is None:
        return checks, None, None, None
    entry = ordered[-1].close
    stop = low if direction == Direction.LONG else high
    return checks, direction, entry, stop
