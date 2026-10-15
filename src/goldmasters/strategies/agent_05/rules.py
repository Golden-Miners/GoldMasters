"""Agent 5 rule composition: governing trend first, pullback second.

Pullbacks in an established trend offer clearer invalidation than chasing
extension — so trend direction governs before any pullback shape is read,
and a pullback that breaks the governing trend rejects. Missing numerics
yield ``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import ema_close
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent05Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    trend_period: int | None
    pullback_ma: int | None
    confirm_bars: int | None
    expiry_bars: int | None


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


def rule_governing_trend(
    bars: Sequence[MarketBar], params: Agent05Params
) -> tuple[RuleCheck, Direction | None]:
    """The trend average must slope in one direction; flat is no setup."""
    if params.trend_period is None or params.confirm_bars is None:
        return (
            _check(
                "governing-trend",
                "unknown",
                "unconfigured trend window",
                "fail-closed: trend_period/confirm_bars unset",
                {},
            ),
            None,
        )
    ordered = list(bars)
    if len(ordered) <= params.confirm_bars:
        return (
            _check(
                "governing-trend",
                "unknown",
                "trend slope indeterminate on short history",
                "slope window exceeds the bars under evaluation",
                {},
            ),
            None,
        )
    now = ema_close(ordered, period=params.trend_period)
    earlier = ema_close(ordered[: len(ordered) - params.confirm_bars], period=params.trend_period)
    if now is None or earlier is None:
        return (
            _check(
                "governing-trend",
                "unknown",
                "trend average indeterminate on short history",
                "trend window exceeds the bars under evaluation",
                {},
            ),
            None,
        )
    inputs = {"trend_now": str(now), "trend_earlier": str(earlier)}
    if now > earlier:
        return (
            _check(
                "governing-trend",
                "pass",
                f"governing trend rises {earlier} to {now}",
                "pullback continuation: uptrend governs",
                inputs,
            ),
            Direction.LONG,
        )
    if now < earlier:
        return (
            _check(
                "governing-trend",
                "pass",
                f"governing trend falls {earlier} to {now}",
                "pullback continuation: downtrend governs",
                inputs,
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "governing-trend",
            "fail",
            f"governing trend flat at {now}: no trend to pull back to",
            "pullback continuation: trendless market",
            inputs,
        ),
        None,
    )


def rule_pullback_shape(
    bars: Sequence[MarketBar],
    params: Agent05Params,
    direction: Direction | None,
) -> tuple[RuleCheck, Decimal | None]:
    """Price touched the pullback average and closed back on the trend side."""
    if params.pullback_ma is None:
        return (
            _check(
                "pullback-shape",
                "unknown",
                "unconfigured pullback average",
                "fail-closed: pullback_ma unset",
                {},
            ),
            None,
        )
    ordered = list(bars)
    average = ema_close(ordered, period=params.pullback_ma)
    if average is None or direction is None:
        return (
            _check(
                "pullback-shape",
                "unknown",
                "pullback shape indeterminate without trend direction",
                "no governing trend from the trend rule",
                {},
            ),
            None,
        )
    window = ordered[len(ordered) - params.pullback_ma :]
    if direction == Direction.LONG:
        touched = min(bar.low for bar in window) <= average
        recovered = ordered[-1].close > average
    else:
        touched = max(bar.high for bar in window) >= average
        recovered = ordered[-1].close < average
    inputs = {"pullback_ma": str(average), "last_close": str(ordered[-1].close)}
    if touched and recovered:
        extreme = min(bar.low for bar in window) if direction == Direction.LONG else max(
            bar.high for bar in window
        )
        return (
            _check(
                "pullback-shape",
                "pass",
                f"pullback touched {average} and recovered",
                "pullback continuation: pullback with confirmation",
                inputs,
            ),
            extreme,
        )
    return (
        _check(
            "pullback-shape",
            "fail",
            f"no pullback touch of {average} with recovery",
            "pullback continuation: extension, not a pullback",
            inputs,
        ),
        None,
    )


def rule_entry_confirmation(
    bars: Sequence[MarketBar],
    params: Agent05Params,
    direction: Direction | None,
) -> RuleCheck:
    """Documented confirmation: recent closes hold the trend side."""
    if params.pullback_ma is None or params.confirm_bars is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "unconfigured confirmation span",
            "fail-closed: pullback_ma/confirm_bars unset",
            {},
        )
    ordered = list(bars)
    average = ema_close(ordered, period=params.pullback_ma)
    if average is None or direction is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "confirmation indeterminate without trend direction",
            "no governing trend from the trend rule",
            {},
        )
    span = ordered[len(ordered) - params.confirm_bars :]
    if direction == Direction.LONG:
        held = all(bar.close > average for bar in span)
    else:
        held = all(bar.close < average for bar in span)
    inputs = {"closes": ",".join(str(bar.close) for bar in span), "average": str(average)}
    if held:
        return _check(
            "entry-confirmation",
            "pass",
            f"last {params.confirm_bars} closes hold the trend side of {average}",
            "pullback continuation: entry confirmation present",
            inputs,
        )
    return _check(
        "entry-confirmation",
        "fail",
        f"a recent close lost the trend side of {average}",
        "pullback continuation: entry confirmation absent",
        inputs,
    )


def rule_pullback_expiry(
    bars: Sequence[MarketBar], params: Agent05Params, extreme_index: int | None
) -> RuleCheck:
    """The pullback extreme must sit inside the expiry window."""
    if params.expiry_bars is None or extreme_index is None:
        return _check(
            "pullback-expiry",
            "unknown",
            "unconfigured expiry window",
            "fail-closed: expiry_bars unset or no pullback extreme",
            {},
        )
    fresh = extreme_index >= len(list(bars)) - params.expiry_bars
    inputs = {"extreme_bar": str(extreme_index), "expiry_bars": str(params.expiry_bars)}
    if fresh:
        return _check(
            "pullback-expiry",
            "pass",
            f"pullback extreme at bar {extreme_index} inside the expiry window",
            "pullback continuation: pullback not expired",
            inputs,
        )
    return _check(
        "pullback-expiry",
        "fail",
        f"pullback extreme at bar {extreme_index} older than {params.expiry_bars} bars",
        "pullback continuation: stale pullback",
        inputs,
    )


def rule_trend_intact(
    direction: Direction | None, ctx: MarketContext, extreme: Decimal | None
) -> RuleCheck:
    """Reject pullbacks that break the governing trend; ranges stay indeterminate."""
    if direction is None:
        return _check(
            "trend-intact",
            "unknown",
            "trend integrity indeterminate without direction",
            "no governing trend from the trend rule",
            {},
        )
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "trend-intact",
            "unknown",
            "ranging market: no governing trend to hold",
            "pullback continuation: range-bound regime",
            {"regime": ctx.regime.value},
        )
    aligned = (direction == Direction.LONG and ctx.regime == TrendRegime.UPTREND) or (
        direction == Direction.SHORT and ctx.regime == TrendRegime.DOWNTREND
    )
    if aligned and extreme is not None:
        return _check(
            "trend-intact",
            "pass",
            f"pullback extreme {extreme} respects the governing trend",
            "pullback continuation: trend intact",
            {"regime": ctx.regime.value, "extreme": str(extreme)},
        )
    return _check(
        "trend-intact",
        "fail",
        f"regime {ctx.regime.value} breaks the governing trend",
        "pullback continuation: pullback broke the trend",
        {"regime": ctx.regime.value},
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent05Params
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the five operator rules; stop is the structural extreme."""
    ordered = list(bars)
    trend, direction = rule_governing_trend(ordered, params)
    shape, _ = rule_pullback_shape(ordered, params, direction)
    confirmation = rule_entry_confirmation(ordered, params, direction)
    window = (
        ordered[len(ordered) - params.pullback_ma - params.expiry_bars :]
        if params.pullback_ma is not None and params.expiry_bars is not None
        else ordered
    )
    if direction == Direction.LONG:
        extremes = [bar.low for bar in window]
        extreme = min(extremes)
        extreme_index = len(ordered) - len(window) + extremes.index(extreme)
    elif direction == Direction.SHORT:
        extremes = [bar.high for bar in window]
        extreme = max(extremes)
        extreme_index = len(ordered) - len(window) + extremes.index(extreme)
    else:
        extreme, extreme_index = None, None
    expiry = rule_pullback_expiry(ordered, params, extreme_index)
    intact = rule_trend_intact(direction, ctx, extreme)
    checks = [trend, shape, confirmation, expiry, intact]
    if direction is None or extreme is None:
        return checks, None, None, None
    entry = ordered[-1].close
    stop = (
        min(bar.low for bar in ordered)
        if direction == Direction.LONG
        else max(bar.high for bar in ordered)
    )
    return checks, direction, entry, stop
