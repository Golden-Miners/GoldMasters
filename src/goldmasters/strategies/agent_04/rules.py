"""Agent 4 rule composition: compression first, direction second.

Low-volatility compression can precede directional expansion, but expansion
alone never predicts direction — so the compression gate and the directional
breakout confirmation are separate rules, plus a gap/reliability filter.
Implementation and evaluation stay distinct from Agent 3. Missing numerics
yield ``unknown`` (fail-closed).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import average_true_range
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent04Params:
    """Settings-derived row: scope lists plus operator-spec numerics.

    ``compression_pctile`` is a fraction over the trailing volatility
    readings (operator confirms the scale with the other thresholds).
    """

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    vol_lookback: int | None
    compression_pctile: Decimal | None
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


def trailing_atrs(bars: Sequence[MarketBar], vol_lookback: int) -> list[Decimal] | None:
    """Current plus prior ATR readings, newest first; ``None`` when short.

    Each reading consumes only its own prefix, so no future bar leaks into
    an earlier reading.
    """
    ordered = list(bars)
    readings: list[Decimal] = []
    for dropped in range(vol_lookback + 1):
        prefix = ordered[: len(ordered) - dropped] if dropped else ordered
        atr = average_true_range(prefix, period=vol_lookback)
        if atr is None:
            return None
        readings.append(atr)
    return readings


def rule_compression(
    readings: list[Decimal] | None, params: Agent04Params
) -> tuple[RuleCheck, Decimal | None]:
    """Current volatility must rank at or below the compression fraction."""
    if readings is None or params.compression_pctile is None:
        return (
            _check(
                "vol-compression",
                "unknown",
                "compression indeterminate on short history",
                "fail-closed: vol window or compression_pctile unset",
                {},
            ),
            None,
        )
    current = readings[0]
    ranked = sum(1 for reading in readings if reading <= current)
    fraction = Decimal(ranked) / Decimal(len(readings))
    inputs = {
        "current_atr": str(current),
        "rank_fraction": str(fraction),
        "pctile": str(params.compression_pctile),
    }
    if fraction <= params.compression_pctile:
        return (
            _check(
                "vol-compression",
                "pass",
                f"current ATR {current} ranks {fraction} of trailing volatility",
                "vol-expansion breakout: compression precedes",
                inputs,
            ),
            current,
        )
    return (
        _check(
            "vol-compression",
            "fail",
            f"current ATR {current} ranks {fraction}: no compression",
            "vol-expansion breakout: volatility not compressed",
            inputs,
        ),
        current,
    )


def rule_directional_breakout(
    bars: Sequence[MarketBar],
    params: Agent04Params,
    atr: Decimal | None,
) -> tuple[RuleCheck, Direction | None]:
    """Separate directional confirmation: displacement must clear one ATR."""
    if params.confirm_bars is None or atr is None:
        return (
            _check(
                "directional-breakout",
                "unknown",
                "direction indeterminate without compression read",
                "no volatility baseline for the expansion leg",
                {},
            ),
            None,
        )
    ordered = list(bars)
    if len(ordered) <= params.confirm_bars:
        return (
            _check(
                "directional-breakout",
                "unknown",
                "displacement window exceeds the bars under evaluation",
                "confirmation span longer than history",
                {},
            ),
            None,
        )
    displacement = ordered[-1].close - ordered[len(ordered) - params.confirm_bars - 1].close
    inputs = {"displacement": str(displacement), "atr": str(atr)}
    if displacement >= atr:
        return (
            _check(
                "directional-breakout",
                "pass",
                f"upward displacement {displacement} clears ATR {atr}",
                "vol-expansion breakout: directional confirmation long",
                inputs,
            ),
            Direction.LONG,
        )
    if displacement <= -atr:
        return (
            _check(
                "directional-breakout",
                "pass",
                f"downward displacement {displacement} clears ATR {atr}",
                "vol-expansion breakout: directional confirmation short",
                inputs,
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "directional-breakout",
            "fail",
            f"displacement {displacement} inside one ATR {atr}: expansion without direction",
            "vol-expansion breakout: expansion alone predicts no direction",
            inputs,
        ),
        None,
    )


def rule_reliability(
    bars: Sequence[MarketBar], params: Agent04Params, atr: Decimal | None
) -> RuleCheck:
    """Gap filter: overnight-style gaps mark unreliable candles, not setups."""
    if params.confirm_bars is None or atr is None:
        return _check(
            "candle-reliability",
            "unknown",
            "reliability indeterminate without a volatility baseline",
            "no ATR baseline for the gap filter",
            {},
        )
    ordered = list(bars)
    span = ordered[len(ordered) - params.confirm_bars - 1 :]
    gaps = [abs(bar.open - span[index - 1].close) for index, bar in enumerate(span) if index]
    worst = max(gaps) if gaps else Decimal(0)
    inputs = {"worst_gap": str(worst), "atr": str(atr)}
    if worst <= atr:
        return _check(
            "candle-reliability",
            "pass",
            f"worst gap {worst} inside ATR {atr}",
            "vol-expansion breakout: candles reliable",
            inputs,
        )
    return _check(
        "candle-reliability",
        "fail",
        f"worst gap {worst} exceeds ATR {atr}: unreliable candles filtered",
        "vol-expansion breakout: gap filter rejects",
        inputs,
    )


def rule_regime(direction: Direction | None, ctx: MarketContext) -> RuleCheck:
    """Range-bound markets leave expansion indeterminate; opposed trends reject."""
    if direction is None:
        return _check(
            "regime-confirmation",
            "unknown",
            "regime confirmation indeterminate without direction",
            "no directional expansion to confirm",
            {},
        )
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "regime-confirmation",
            "unknown",
            "ranging market: expansion has no trend to join",
            "vol-expansion breakout: range-bound regime",
            {"regime": ctx.regime.value},
        )
    aligned = (direction == Direction.LONG and ctx.regime == TrendRegime.UPTREND) or (
        direction == Direction.SHORT and ctx.regime == TrendRegime.DOWNTREND
    )
    if aligned:
        return _check(
            "regime-confirmation",
            "pass",
            f"regime {ctx.regime.value} confirms the expansion",
            "vol-expansion breakout: regime confirms",
            {"regime": ctx.regime.value},
        )
    return _check(
        "regime-confirmation",
        "fail",
        f"regime {ctx.regime.value} opposes the expansion",
        "vol-expansion breakout: regime rejects",
        {"regime": ctx.regime.value},
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent04Params
) -> tuple[list[RuleCheck], Direction | None, Decimal | None, Decimal | None]:
    """Compose the four operator rules; stop is the structural swing extreme."""
    ordered = list(bars)
    readings = (
        trailing_atrs(ordered, params.vol_lookback) if params.vol_lookback is not None else None
    )
    compression, atr = rule_compression(readings, params)
    breakout, direction = rule_directional_breakout(ordered, params, atr)
    reliability = rule_reliability(ordered, params, atr)
    regime = rule_regime(direction, ctx)
    checks = [compression, breakout, reliability, regime]
    if direction is None:
        return checks, None, None, None
    entry = ordered[-1].close
    stop = (
        min(bar.low for bar in ordered)
        if direction == Direction.LONG
        else max(bar.high for bar in ordered)
    )
    return checks, direction, entry, stop
