"""Agent 7 rule composition: range gate first, extension evidence second.

In range-bound regimes, unusually large deviations from a reference
distribution may partially reverse — so the range gate runs before any
extension read, and strong trends never auto-fade. Extension needs both the
Bollinger band and the z-score to agree plus an RSI extreme on the same side;
reversal confirmation requires the latest step back toward the reference.
Missing numerics yield ``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import rsi_close, sma_close, stdev_close
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent07Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    basis_period: int | None
    band_width: Decimal | None
    z_min: Decimal | None
    rsi_period: int | None
    rsi_extreme: Decimal | None
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


def _basis(
    bars: Sequence[MarketBar], params: Agent07Params
) -> tuple[Decimal | None, Decimal | None]:
    """Reference mean and dispersion over the basis window (shared read)."""
    if params.basis_period is None:
        return None, None
    ordered = list(bars)
    return sma_close(ordered, period=params.basis_period), stdev_close(
        ordered, period=params.basis_period
    )


def rule_range_gate(ctx: MarketContext) -> RuleCheck:
    """Range-bound regime first; strong trends never auto-fade."""
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "range-regime-gate",
            "pass",
            "regime is range-bound: mean reversion may apply",
            "mean reversion: range gate satisfied",
            {"regime": ctx.regime.value},
        )
    return _check(
        "range-regime-gate",
        "fail",
        f"regime {ctx.regime.value} is not range-bound: never fade a trend",
        "mean reversion: trend regime rejects",
        {"regime": ctx.regime.value},
    )


def rule_band_extension(
    bars: Sequence[MarketBar], params: Agent07Params
) -> tuple[RuleCheck, Direction | None, Decimal | None]:
    """Bollinger band plus z-score agree on an extended deviation.

    Direction points back toward the reference (extended above means short).
    Returns the basis for confirmation and the reference-price target.
    """
    if params.basis_period is None or params.band_width is None or params.z_min is None:
        return (
            _check(
                "band-extension",
                "unknown",
                "unconfigured basis window, band width or z floor",
                "fail-closed: basis_period/band_width/z_min unset",
                {},
            ),
            None,
            None,
        )
    basis, dispersion = _basis(bars, params)
    if basis is None or dispersion is None:
        return (
            _check(
                "band-extension",
                "unknown",
                "reference distribution indeterminate on short history",
                "basis window exceeds the bars under evaluation",
                {},
            ),
            None,
            None,
        )
    ordered = list(bars)
    deviation = ordered[-1].close - basis
    if dispersion == 0:
        return (
            _check(
                "band-extension",
                "fail",
                f"no dispersion around {basis}: flat, not extended",
                "mean reversion: no deviation from the reference",
                {"basis": str(basis)},
            ),
            None,
            None,
        )
    band = params.band_width * dispersion
    z_score = deviation / dispersion
    inputs = {"basis": str(basis), "band": str(band), "z": str(z_score)}
    direction = Direction.SHORT if deviation > 0 else Direction.LONG
    if abs(deviation) >= band and abs(z_score) >= params.z_min:
        side = "above" if deviation > 0 else "below"
        return (
            _check(
                "band-extension",
                "pass",
                f"deviation {deviation} {side} {basis} clears band {band} at z {z_score}",
                "mean reversion: band and z-score agree on extension",
                inputs,
            ),
            direction,
            basis,
        )
    return (
        _check(
            "band-extension",
            "fail",
            f"deviation {deviation} inside band {band} at z {z_score}: not extended",
            "mean reversion: no unusual deviation",
            inputs,
        ),
        None,
        None,
    )


def rule_rsi_extreme(
    bars: Sequence[MarketBar],
    params: Agent07Params,
    direction: Direction | None,
) -> RuleCheck:
    """RSI extreme concurs on the same side; flat windows stay unknown.

    The extreme rides ``rsi_extreme`` directly: oversold at or below it
    (long), overbought at or above ``100 - extreme`` (short) — the operator
    confirms the scale with the other thresholds.
    """
    if params.rsi_period is None or params.rsi_extreme is None or direction is None:
        return _check(
            "rsi-extreme",
            "unknown",
            "unconfigured RSI window or extreme, or no extension direction",
            "fail-closed: rsi_period/rsi_extreme unset or no direction",
            {},
        )
    strength = rsi_close(list(bars), period=params.rsi_period)
    if strength is None:
        return _check(
            "rsi-extreme",
            "unknown",
            "RSI indeterminate on short or flat history",
            "RSI window exceeds the bars under evaluation",
            {},
        )
    inputs = {"rsi": str(strength), "extreme": str(params.rsi_extreme)}
    if direction == Direction.LONG:
        if strength <= params.rsi_extreme:
            return _check(
                "rsi-extreme",
                "pass",
                f"RSI {strength} at or below {params.rsi_extreme}: oversold",
                "mean reversion: RSI concurs on the long side",
                inputs,
            )
    elif strength >= Decimal(100) - params.rsi_extreme:
        return _check(
            "rsi-extreme",
            "pass",
            f"RSI {strength} at or above {Decimal(100) - params.rsi_extreme}: overbought",
            "mean reversion: RSI concurs on the short side",
            inputs,
        )
    return _check(
        "rsi-extreme",
        "fail",
        f"RSI {strength} not extreme for the {direction.value} side",
        "mean reversion: RSI does not concur",
        inputs,
    )


def rule_reversal_confirmation(
    bars: Sequence[MarketBar],
    params: Agent07Params,
    direction: Direction | None,
    basis: Decimal | None,
) -> RuleCheck:
    """Reversal confirmation: the latest step moves back toward the reference."""
    if params.confirm_bars is None or direction is None or basis is None:
        return _check(
            "reversal-confirmation",
            "unknown",
            "unconfigured confirmation span, or no extension to confirm",
            "fail-closed: confirm_bars unset or no direction",
            {},
        )
    ordered = list(bars)
    if len(ordered) < params.confirm_bars + 1:
        return _check(
            "reversal-confirmation",
            "unknown",
            "confirmation span exceeds the bars under evaluation",
            "span window exceeds the bars under evaluation",
            {},
        )
    move = ordered[-1].close - ordered[-2].close
    deviation = ordered[-2].close - basis
    toward = (deviation > 0 and move < 0) or (deviation < 0 and move > 0)
    inputs = {"move": str(move), "basis": str(basis)}
    if toward:
        return _check(
            "reversal-confirmation",
            "pass",
            f"latest step {move} moves back toward {basis}: reversal underway",
            "mean reversion: reversal confirmation present",
            inputs,
        )
    return _check(
        "reversal-confirmation",
        "fail",
        f"latest step {move} extends away from {basis}: no reversal yet",
        "mean reversion: reversal confirmation absent",
        inputs,
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent07Params
) -> tuple[
    list[RuleCheck], Direction | None, Decimal | None, Decimal | None, Decimal | None
]:
    """Compose the four operator rules; stop is structural, target is the basis."""
    ordered = list(bars)
    gate = rule_range_gate(ctx)
    extension, direction, basis = rule_band_extension(ordered, params)
    extreme = rule_rsi_extreme(ordered, params, direction)
    confirmation = rule_reversal_confirmation(ordered, params, direction, basis)
    checks = [gate, extension, extreme, confirmation]
    if direction is None or basis is None:
        return checks, None, None, None, None
    entry = ordered[-1].close
    lows = [bar.low for bar in ordered]
    highs = [bar.high for bar in ordered]
    stop = min(lows) if direction == Direction.LONG else max(highs)
    return checks, direction, entry, stop, basis
