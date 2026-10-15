"""Agent 1 rule composition: fast/slow average relationship + filters.

Rules consume bars, ctx and settings params only; shared arithmetic reuses
domain/indicators.py (never re-implemented here). Threshold comparisons cite
the operator rule text in evidence; a missing numeric (None) yields
``unknown`` (fail-closed, never a default).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import average_true_range, ema_close
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent01Params:
    """Settings-derived row: scope lists plus operator-spec numerics.

    Every numeric stays ``None`` until the operator sets its
    ``GOLDMASTERS_STRATEGY_AGENT_01_*`` key; ``None`` fails closed.
    """

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    fast_period: int | None
    slow_period: int | None
    htf_timeframe: str | None
    adx_min: Decimal | None
    confirm_bars: int | None


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


def rule_trend_alignment(
    bars: Sequence[MarketBar], params: Agent01Params
) -> tuple[RuleCheck, Direction | None]:
    """Fast/slow relationship sets direction; equality is chop (fail)."""
    if params.fast_period is None or params.slow_period is None:
        return (
            _check(
                "trend-alignment",
                "unknown",
                "unconfigured average period",
                "fail-closed: fast/slow period unset",
                {},
            ),
            None,
        )
    fast = ema_close(bars, period=params.fast_period)
    slow = ema_close(bars, period=params.slow_period)
    if fast is None or slow is None:
        return (
            _check(
                "trend-alignment",
                "unknown",
                "averages indeterminate on short history",
                "insufficient bars for the configured average windows",
                {},
            ),
            None,
        )
    inputs = {"fast_ema": str(fast), "slow_ema": str(slow)}
    if fast > slow:
        return (
            _check(
                "trend-alignment",
                "pass",
                f"fast average {fast} above slow average {slow}",
                "trend-following: fast/slow relationship favors long",
                inputs,
            ),
            Direction.LONG,
        )
    if fast < slow:
        return (
            _check(
                "trend-alignment",
                "pass",
                f"fast average {fast} below slow average {slow}",
                "trend-following: fast/slow relationship favors short",
                inputs,
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "trend-alignment",
            "fail",
            f"averages equal at {fast}: crossover alone never suffices in chop",
            "trend-following: no directional relationship",
            inputs,
        ),
        None,
    )


def rule_strength(
    bars: Sequence[MarketBar],
    params: Agent01Params,
    reference_index: int,
) -> RuleCheck:
    """ATR-normalized displacement over the confirmation span (strength leg).

    The operator strength filter (ADX where supported) rides ``adx_min`` as
    the displacement multiple of ATR; ``None`` fails closed.
    """
    if params.adx_min is None or params.confirm_bars is None or params.slow_period is None:
        return _check(
            "trend-strength",
            "unknown",
            "unconfigured strength threshold",
            "fail-closed: adx_min/confirm/slow period unset",
            {},
        )
    atr = average_true_range(bars, period=params.slow_period)
    if atr is None or reference_index >= len(bars):
        return _check(
            "trend-strength",
            "unknown",
            "strength indeterminate on short history",
            "ATR window exceeds the bars under evaluation",
            {},
        )
    displacement = abs(bars[-1].close - bars[reference_index].close)
    required = params.adx_min * atr
    inputs = {
        "displacement": str(displacement),
        "required": str(required),
        "atr": str(atr),
    }
    if displacement >= required:
        return _check(
            "trend-strength",
            "pass",
            f"displacement {displacement} clears {required}",
            "trend-following: strength filter satisfied",
            inputs,
        )
    return _check(
        "trend-strength",
        "fail",
        f"displacement {displacement} below {required}: chop, not trend",
        "trend-following: strength filter rejects",
        inputs,
    )


def rule_confirmation(
    bars: Sequence[MarketBar],
    params: Agent01Params,
    direction: Direction | None,
) -> RuleCheck:
    """Entry confirmation: recent closes hold the trend side of slow average."""
    if params.confirm_bars is None or params.slow_period is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "unconfigured confirmation span",
            "fail-closed: confirm_bars/slow period unset",
            {},
        )
    slow = ema_close(bars, period=params.slow_period)
    if slow is None or direction is None:
        return _check(
            "entry-confirmation",
            "unknown",
            "confirmation indeterminate without trend direction",
            "no governing direction from trend alignment",
            {},
        )
    span = list(bars[len(bars) - params.confirm_bars :])
    if direction == Direction.LONG:
        held = all(bar.close > slow for bar in span)
    else:
        held = all(bar.close < slow for bar in span)
    inputs = {"closes": ",".join(str(bar.close) for bar in span), "slow_ema": str(slow)}
    if held:
        return _check(
            "entry-confirmation",
            "pass",
            f"last {params.confirm_bars} closes hold the trend side of {slow}",
            "trend-following: entry confirmation present",
            inputs,
        )
    return _check(
        "entry-confirmation",
        "fail",
        f"a recent close lost the trend side of {slow}",
        "trend-following: entry confirmation absent",
        inputs,
    )


def rule_htf_filter(
    direction: Direction | None, ctx: MarketContext, params: Agent01Params
) -> RuleCheck:
    """Higher-timeframe trend filter, read through the ctx regime proxy."""
    if params.htf_timeframe is None:
        return _check(
            "htf-trend-filter",
            "unknown",
            "unconfigured higher timeframe",
            "fail-closed: htf_timeframe unset",
            {},
        )
    try:
        higher = Timeframe(params.htf_timeframe)
    except ValueError:
        return _check(
            "htf-trend-filter",
            "unknown",
            f"higher timeframe {params.htf_timeframe!r} is not a known timeframe",
            "fail-closed: htf_timeframe names no timeframe",
            {},
        )
    if direction is None:
        return _check(
            "htf-trend-filter",
            "unknown",
            "higher-timeframe filter indeterminate without direction",
            "no governing direction from trend alignment",
            {},
        )
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "htf-trend-filter",
            "unknown",
            f"higher timeframe {higher.value} regime is ranging: filter indeterminate",
            "trend-following: range-bound higher timeframe",
            {"htf": higher.value},
        )
    aligned = (direction == Direction.LONG and ctx.regime == TrendRegime.UPTREND) or (
        direction == Direction.SHORT and ctx.regime == TrendRegime.DOWNTREND
    )
    if aligned:
        return _check(
            "htf-trend-filter",
            "pass",
            f"higher timeframe {higher.value} regime {ctx.regime.value} aligns",
            "trend-following: higher-timeframe filter satisfied",
            {"htf": higher.value, "regime": ctx.regime.value},
        )
    return _check(
        "htf-trend-filter",
        "fail",
        f"higher timeframe {higher.value} regime {ctx.regime.value} opposes",
        "trend-following: higher-timeframe filter rejects",
        {"htf": higher.value, "regime": ctx.regime.value},
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent01Params
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the four operator rules; derive entry/stop only on direction."""
    ordered = list(bars)
    alignment, direction = rule_trend_alignment(ordered, params)
    reference = (
        len(ordered) - params.confirm_bars - 1 if params.confirm_bars is not None else len(ordered)
    )
    strength = rule_strength(ordered, params, reference)
    confirmation = rule_confirmation(ordered, params, direction)
    htf = rule_htf_filter(direction, ctx, params)
    checks = [alignment, strength, confirmation, htf]
    if direction is None:
        return checks, None, None, None
    entry = ordered[-1].close
    lows = [bar.low for bar in ordered]
    highs = [bar.high for bar in ordered]
    stop = min(lows) if direction == Direction.LONG else max(highs)
    return checks, direction, entry, stop
