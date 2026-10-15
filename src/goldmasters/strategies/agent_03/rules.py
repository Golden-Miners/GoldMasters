"""Agent 3 rule composition: prior-channel break with buffer and freshness.

The channel forms from prior completed candles only (the confirmation span
is excluded); long and short are evaluated separately. Missing numerics
yield ``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent03Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    channel_bars: int | None
    buffer_ticks: int | None
    confirm_bars: int | None
    exit_bars: int | None


@dataclass(frozen=True)
class Channel:
    """Prior-channel edges plus the edge-bar positions (freshness evidence)."""

    upper: Decimal
    lower: Decimal
    high_bar_index: int
    low_bar_index: int


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


def prior_channel(bars: Sequence[MarketBar], params: Agent03Params) -> Channel | None:
    """Upper/lower edges from the channel window before the confirmation span."""
    ordered = list(bars)
    if params.channel_bars is None or params.confirm_bars is None:
        return None
    if len(ordered) < params.channel_bars + params.confirm_bars:
        return None
    start = len(ordered) - params.channel_bars - params.confirm_bars
    stop = len(ordered) - params.confirm_bars
    window = ordered[start:stop]
    highs = [bar.high for bar in window]
    lows = [bar.low for bar in window]
    upper = max(highs)
    lower = min(lows)
    base = len(ordered) - params.channel_bars - params.confirm_bars
    return Channel(
        upper=upper,
        lower=lower,
        high_bar_index=base + highs.index(upper),
        low_bar_index=base + lows.index(lower),
    )


def rule_channel_break(
    bars: Sequence[MarketBar], channel: Channel | None
) -> tuple[RuleCheck, Direction | None]:
    """The latest close breaks a channel edge; inside the channel is no setup."""
    if channel is None:
        return (
            _check(
                "channel-break",
                "unknown",
                "channel indeterminate on short history",
                "channel window exceeds the bars under evaluation",
                {},
            ),
            None,
        )
    close = list(bars)[-1].close
    inputs = {"close": str(close), "upper": str(channel.upper), "lower": str(channel.lower)}
    if close > channel.upper:
        return (
            _check(
                "channel-break",
                "pass",
                f"close {close} breaks upper channel {channel.upper}",
                "donchian breakout favors long",
                inputs,
            ),
            Direction.LONG,
        )
    if close < channel.lower:
        return (
            _check(
                "channel-break",
                "pass",
                f"close {close} breaks lower channel {channel.lower}",
                "donchian breakout favors short",
                inputs,
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "channel-break",
            "fail",
            f"close {close} sits inside {channel.lower}-{channel.upper}",
            "donchian breakout: no channel break",
            inputs,
        ),
        None,
    )


def rule_confirmation(
    bars: Sequence[MarketBar],
    channel: Channel | None,
    params: Agent03Params,
    direction: Direction | None,
) -> RuleCheck:
    """Every close in the confirmation span sits beyond the broken edge."""
    if channel is None or params.confirm_bars is None or direction is None:
        return _check(
            "breakout-confirmation",
            "unknown",
            "confirmation indeterminate without a channel break",
            "no broken edge to confirm against",
            {},
        )
    ordered = list(bars)
    span = ordered[len(ordered) - params.confirm_bars :]
    if direction == Direction.LONG:
        held = all(bar.close > channel.upper for bar in span)
        edge = channel.upper
    else:
        held = all(bar.close < channel.lower for bar in span)
        edge = channel.lower
    inputs = {"closes": ",".join(str(bar.close) for bar in span), "edge": str(edge)}
    if held:
        return _check(
            "breakout-confirmation",
            "pass",
            f"confirmation span holds beyond {edge}",
            "donchian breakout: confirmed break",
            inputs,
        )
    return _check(
        "breakout-confirmation",
        "fail",
        f"confirmation span re-enters {edge}: false-breakout handling rejects",
        "donchian breakout: unconfirmed break",
        inputs,
    )


def rule_buffer(
    bars: Sequence[MarketBar],
    channel: Channel | None,
    params: Agent03Params,
    direction: Direction | None,
    tick: Decimal,
) -> RuleCheck:
    """Breakout excess must clear the configured buffer in ticks."""
    if channel is None or params.buffer_ticks is None or direction is None:
        return _check(
            "breakout-buffer",
            "unknown",
            "unconfigured breakout buffer",
            "fail-closed: buffer_ticks unset",
            {},
        )
    close = list(bars)[-1].close
    if direction == Direction.LONG:
        excess = close - channel.upper
    else:
        excess = channel.lower - close
    required = Decimal(params.buffer_ticks) * tick
    inputs = {"excess": str(excess), "required": str(required)}
    if excess >= required:
        return _check(
            "breakout-buffer",
            "pass",
            f"excess {excess} clears buffer {required}",
            "donchian breakout: buffer satisfied",
            inputs,
        )
    return _check(
        "breakout-buffer",
        "fail",
        f"excess {excess} inside buffer {required}: noise, not expansion",
        "donchian breakout: buffer rejects",
        inputs,
    )


def rule_regime(direction: Direction | None, ctx: MarketContext) -> RuleCheck:
    """Range-bound markets leave channel breaks indeterminate."""
    if direction is None:
        return _check(
            "regime-confirmation",
            "unknown",
            "regime confirmation indeterminate without direction",
            "no channel break to confirm",
            {},
        )
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "regime-confirmation",
            "unknown",
            "ranging market: channel break has no trend to continue",
            "donchian breakout: range-bound regime",
            {"regime": ctx.regime.value},
        )
    aligned = (direction == Direction.LONG and ctx.regime == TrendRegime.UPTREND) or (
        direction == Direction.SHORT and ctx.regime == TrendRegime.DOWNTREND
    )
    if aligned:
        return _check(
            "regime-confirmation",
            "pass",
            f"regime {ctx.regime.value} confirms the break",
            "donchian breakout: trend/regime confirmation",
            {"regime": ctx.regime.value},
        )
    return _check(
        "regime-confirmation",
        "fail",
        f"regime {ctx.regime.value} opposes the break",
        "donchian breakout: regime rejects",
        {"regime": ctx.regime.value},
    )


def rule_exit_freshness(
    bars: Sequence[MarketBar],
    channel: Channel | None,
    params: Agent03Params,
    direction: Direction | None,
) -> RuleCheck:
    """The broken edge formed inside the time/channel exit horizon."""
    if channel is None or params.exit_bars is None or direction is None:
        return _check(
            "exit-freshness",
            "unknown",
            "unconfigured exit horizon",
            "fail-closed: exit_bars unset",
            {},
        )
    edge_index = channel.high_bar_index if direction == Direction.LONG else channel.low_bar_index
    fresh = edge_index >= len(list(bars)) - params.exit_bars
    inputs = {"edge_bar": str(edge_index), "exit_bars": str(params.exit_bars)}
    if fresh:
        return _check(
            "exit-freshness",
            "pass",
            f"broken edge at bar {edge_index} inside the exit horizon",
            "donchian breakout: channel still tradeable",
            inputs,
        )
    return _check(
        "exit-freshness",
        "fail",
        f"broken edge at bar {edge_index} older than {params.exit_bars} bars",
        "donchian breakout: stale channel, time exit applies",
        inputs,
    )


def run_rules(
    bars: Sequence[MarketBar],
    ctx: MarketContext,
    params: Agent03Params,
    tick: Decimal,
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the five operator rules; stop is the opposite channel edge."""
    ordered = list(bars)
    channel = prior_channel(ordered, params)
    break_rule, direction = rule_channel_break(ordered, channel)
    confirmation = rule_confirmation(ordered, channel, params, direction)
    buffer = rule_buffer(ordered, channel, params, direction, tick)
    regime = rule_regime(direction, ctx)
    freshness = rule_exit_freshness(ordered, channel, params, direction)
    checks = [break_rule, confirmation, buffer, regime, freshness]
    if direction is None or channel is None:
        return checks, None, None, None
    entry = ordered[-1].close
    stop = channel.lower if direction == Direction.LONG else channel.upper
    return checks, direction, entry, stop
