"""Agent 2 rule composition: own past returns + volatility normalization.

Return-based signal, distinct from Agent 1's crossover logic: direction comes
from historical returns over configurable lookbacks, normalized by ATR risk,
with holding-horizon fit and signal-expiry gates. Missing numerics yield
``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import average_true_range
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent02Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    lookbacks: tuple[int, ...]
    entry_threshold: Decimal | None
    vol_lookback: int | None
    max_hold_bars: int | None
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


def _returns(
    bars: Sequence[MarketBar], lookback: int
) -> Decimal | None:
    """Close-to-close return over the lookback; ``None`` when short."""
    ordered = list(bars)
    if len(ordered) < lookback + 1:
        return None
    base = ordered[len(ordered) - lookback - 1].close
    if base == 0:
        return None
    return (ordered[-1].close - base) / base


def rule_momentum_alignment(
    bars: Sequence[MarketBar], params: Agent02Params
) -> tuple[RuleCheck, Direction | None]:
    """Every configured lookback must clear the entry threshold in one direction."""
    if params.entry_threshold is None or not params.lookbacks:
        return (
            _check(
                "momentum-alignment",
                "unknown",
                "unconfigured lookbacks or threshold",
                "fail-closed: lookbacks/entry_threshold unset",
                {},
            ),
            None,
        )
    rets: dict[int, Decimal] = {}
    for lookback in params.lookbacks:
        ret = _returns(bars, lookback)
        if ret is None:
            return (
                _check(
                    "momentum-alignment",
                    "unknown",
                    f"return over {lookback} bars indeterminate",
                    "history shorter than the configured lookback",
                    {},
                ),
                None,
            )
        rets[lookback] = ret
    inputs = {f"ret_{lookback}": str(ret) for lookback, ret in rets.items()}
    if all(ret >= params.entry_threshold for ret in rets.values()):
        return (
            _check(
                "momentum-alignment",
                "pass",
                f"all lookback returns clear {params.entry_threshold}",
                "time-series momentum favors long",
                inputs,
            ),
            Direction.LONG,
        )
    if all(ret <= -params.entry_threshold for ret in rets.values()):
        return (
            _check(
                "momentum-alignment",
                "pass",
                f"all lookback returns clear -{params.entry_threshold}",
                "time-series momentum favors short",
                inputs,
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "momentum-alignment",
            "fail",
            "lookback returns disagree or sit inside the threshold",
            "time-series momentum: no aligned direction",
            inputs,
        ),
        None,
    )


def rule_vol_normalization(
    bars: Sequence[MarketBar], params: Agent02Params
) -> tuple[RuleCheck, Decimal | None]:
    """ATR risk normalization must be computable and positive."""
    if params.vol_lookback is None:
        return (
            _check(
                "vol-normalization",
                "unknown",
                "unconfigured volatility lookback",
                "fail-closed: vol_lookback unset",
                {},
            ),
            None,
        )
    atr = average_true_range(bars, period=params.vol_lookback)
    if atr is None:
        return (
            _check(
                "vol-normalization",
                "unknown",
                "volatility indeterminate on short history",
                "ATR window exceeds the bars under evaluation",
                {},
            ),
            None,
        )
    if atr <= 0:
        return (
            _check(
                "vol-normalization",
                "fail",
                "zero volatility: no risk to normalize",
                "time-series momentum: degenerate volatility",
                {"atr": str(atr)},
            ),
            None,
        )
    return (
        _check(
            "vol-normalization",
            "pass",
            f"ATR {atr} normalizes the return signal",
            "time-series momentum: volatility leg sound",
            {"atr": str(atr)},
        ),
        atr,
    )


def rule_horizon_fit(params: Agent02Params) -> RuleCheck:
    """The holding horizon must cover the longest lookback evaluated."""
    if params.max_hold_bars is None or not params.lookbacks:
        return _check(
            "horizon-fit",
            "unknown",
            "unconfigured holding horizon",
            "fail-closed: max_hold_bars/lookbacks unset",
            {},
        )
    longest = max(params.lookbacks)
    if params.max_hold_bars >= longest:
        return _check(
            "horizon-fit",
            "pass",
            f"holding horizon {params.max_hold_bars} covers lookback {longest}",
            "time-series momentum: horizon fits the signal",
            {"max_hold_bars": str(params.max_hold_bars), "lookback": str(longest)},
        )
    return _check(
        "horizon-fit",
        "fail",
        f"holding horizon {params.max_hold_bars} shorter than lookback {longest}",
        "time-series momentum: horizon cannot hold the signal",
        {"max_hold_bars": str(params.max_hold_bars), "lookback": str(longest)},
    )


def rule_signal_expiry(
    bars: Sequence[MarketBar],
    params: Agent02Params,
    direction: Direction | None,
) -> RuleCheck:
    """The signal extreme must sit inside the expiry window (fresh signal)."""
    if params.expiry_bars is None:
        return _check(
            "signal-expiry",
            "unknown",
            "unconfigured expiry window",
            "fail-closed: expiry_bars unset",
            {},
        )
    if direction is None:
        return _check(
            "signal-expiry",
            "unknown",
            "expiry indeterminate without direction",
            "no aligned momentum direction",
            {},
        )
    ordered = list(bars)
    window = ordered[len(ordered) - params.expiry_bars :] if params.expiry_bars < len(ordered) else ordered
    closes = [bar.close for bar in ordered]
    extreme = max(closes) if direction == Direction.LONG else min(closes)
    fresh = any(bar.close == extreme for bar in window)
    inputs = {"extreme": str(extreme), "expiry_bars": str(params.expiry_bars)}
    if fresh:
        return _check(
            "signal-expiry",
            "pass",
            f"signal extreme {extreme} inside the last {params.expiry_bars} bars",
            "time-series momentum: signal not expired",
            inputs,
        )
    return _check(
        "signal-expiry",
        "fail",
        f"signal extreme {extreme} older than {params.expiry_bars} bars",
        "time-series momentum: signal expired",
        inputs,
    )


def rule_regime_gate(direction: Direction | None, ctx: MarketContext) -> RuleCheck:
    """Range-bound markets leave momentum indeterminate; opposed trends reject."""
    if direction is None:
        return _check(
            "regime-gate",
            "unknown",
            "regime gate indeterminate without direction",
            "no aligned momentum direction",
            {},
        )
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "regime-gate",
            "unknown",
            "ranging market: momentum has no trend to follow",
            "time-series momentum: range-bound regime",
            {"regime": ctx.regime.value},
        )
    aligned = (direction == Direction.LONG and ctx.regime == TrendRegime.UPTREND) or (
        direction == Direction.SHORT and ctx.regime == TrendRegime.DOWNTREND
    )
    if aligned:
        return _check(
            "regime-gate",
            "pass",
            f"regime {ctx.regime.value} confirms momentum",
            "time-series momentum: regime confirms",
            {"regime": ctx.regime.value},
        )
    return _check(
        "regime-gate",
        "fail",
        f"regime {ctx.regime.value} opposes momentum",
        "time-series momentum: regime rejects",
        {"regime": ctx.regime.value},
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent02Params
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the five operator rules; entry/stop only on aligned direction."""
    ordered = list(bars)
    alignment, direction = rule_momentum_alignment(ordered, params)
    vol, _ = rule_vol_normalization(ordered, params)
    horizon = rule_horizon_fit(params)
    expiry = rule_signal_expiry(ordered, params, direction)
    regime = rule_regime_gate(direction, ctx)
    checks = [alignment, vol, horizon, expiry, regime]
    if direction is None:
        return checks, None, None, None
    entry = ordered[-1].close
    span = max(params.lookbacks) + 1 if params.lookbacks else len(ordered)
    window = ordered[len(ordered) - span :]
    stop = (
        min(bar.low for bar in window)
        if direction == Direction.LONG
        else max(bar.high for bar in window)
    )
    return checks, direction, entry, stop
