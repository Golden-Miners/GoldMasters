"""Agent 9 rule composition: ordered sweep model, HTF bias first, plan last.

A sweep plus confirmed displacement plus structure shift may mark a
reversal or continuation — so the eight ordered steps read in sequence:
HTF bias, external liquidity pool, sweep within tolerance, displacement,
CHOCH/BOS per setup type, FVG and/or OB zone, retest plus confirmation,
then the trade plan (invalidation, stop, target, expiry). Every step
carries its own reason code; a lone OB, FVG, or CHOCH never signals
because all eight must pass. Missing numerics yield ``unknown``
(fail-closed); a broken upstream step fails the steps that read it.
Shared swing and ATR math comes only from ``domain.*``, never from
another agent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import Direction, MarketBar, Timeframe, TrendRegime

from src.goldmasters.domain.indicators import average_true_range
from src.goldmasters.domain.structure import swing_highs, swing_lows
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent09Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    swing_bars: int | None
    equal_tol_ticks: int | None
    sweep_tol_ticks: int | None
    disp_body_min_atr: Decimal | None
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


def _blocked(rule_id: str, reason: str) -> RuleCheck:
    """A step whose upstream step did not pass: fail, never a guess."""
    return _check(rule_id, "fail", f"blocked: {reason}", f"liquidity sweep: {reason}", {})


def _blocked_unknown(rule_id: str, reason: str) -> RuleCheck:
    """A step whose upstream step is unknown: unknown propagates."""
    return _check(rule_id, "unknown", f"blocked: {reason}", f"liquidity sweep: {reason}", {})


def rule_htf_bias(ctx: MarketContext) -> tuple[RuleCheck, Direction | None]:
    """Step 1, HTF bias: the regime names the only tradeable direction.

    Uptrend bias is long, downtrend bias is short; a range-bound regime
    carries no bias, so there is nothing to sweep toward.
    """
    if ctx.regime == TrendRegime.UPTREND:
        return (
            _check(
                "htf-bias",
                "pass",
                "regime is uptrend: long bias only",
                "liquidity sweep: HTF bias long",
                {"regime": ctx.regime.value},
            ),
            Direction.LONG,
        )
    if ctx.regime == TrendRegime.DOWNTREND:
        return (
            _check(
                "htf-bias",
                "pass",
                "regime is downtrend: short bias only",
                "liquidity sweep: HTF bias short",
                {"regime": ctx.regime.value},
            ),
            Direction.SHORT,
        )
    return (
        _check(
            "htf-bias",
            "fail",
            f"regime {ctx.regime.value} names no directional bias",
            "liquidity sweep: no HTF bias, no setup",
            {"regime": ctx.regime.value},
        ),
        None,
    )


def rule_liquidity_pool(
    bars: Sequence[MarketBar],
    tick_size: Decimal | None,
    params: Agent09Params,
    direction: Direction | None,
) -> tuple[RuleCheck, Decimal | None, int | None]:
    """Step 2, external liquidity: equal swing extremes within tolerance.

    The pool reads the pre-sweep window (everything before the last three
    bars, which the ordered model reserves for sweep, displacement, and
    confirmation). Two or more same-side swings cluster within
    ``equal_tol_ticks`` of the extreme; the extreme is the resting
    liquidity. Returns the level and the latest cluster swing index (the
    expiry anchor).
    """
    if direction is None:
        return _blocked("liquidity-pool", "no HTF bias"), None, None
    if params.swing_bars is None or params.equal_tol_ticks is None:
        return (
            _check(
                "liquidity-pool",
                "unknown",
                "unconfigured swing window or equal tolerance",
                "fail-closed: swing_bars/equal_tol_ticks unset",
                {},
            ),
            None,
            None,
        )
    if tick_size is None:
        return (
            _check(
                "liquidity-pool",
                "unknown",
                "unknown tick size: tolerance unpriceable",
                "missing tick size fails closed",
                {},
            ),
            None,
            None,
        )
    window = list(bars)[:-3]
    if len(window) < params.swing_bars * 2 + 1:
        return (
            _check(
                "liquidity-pool",
                "unknown",
                "too few pre-sweep bars for the swing window",
                "liquidity sweep: pool window incomplete",
                {},
            ),
            None,
            None,
        )
    tolerance = Decimal(params.equal_tol_ticks) * tick_size
    if direction == Direction.SHORT:
        swings = swing_highs(
            window, left_bars=params.swing_bars, right_bars=params.swing_bars
        )
        if len(swings) < 2:
            return (
                _check(
                    "liquidity-pool",
                    "fail",
                    "fewer than two swing highs: no external pool",
                    "liquidity sweep: no buy-side pool to sweep",
                    {},
                ),
                None,
                None,
            )
        level = max(point.price for point in swings)
        cluster = [point for point in swings if level - point.price <= tolerance]
        side = "highs"
    else:
        swings = swing_lows(
            window, left_bars=params.swing_bars, right_bars=params.swing_bars
        )
        if len(swings) < 2:
            return (
                _check(
                    "liquidity-pool",
                    "fail",
                    "fewer than two swing lows: no external pool",
                    "liquidity sweep: no sell-side pool to sweep",
                    {},
                ),
                None,
                None,
            )
        level = min(point.price for point in swings)
        cluster = [point for point in swings if point.price - level <= tolerance]
        side = "lows"
    if len(cluster) < 2:
        return (
            _check(
                "liquidity-pool",
                "fail",
                f"swing {side} spread wider than {tolerance}: no equal pool",
                "liquidity sweep: equal-high-low tolerance broken",
                {"tolerance": str(tolerance)},
            ),
            None,
            None,
        )
    pool_index = max(point.index for point in cluster)
    return (
        _check(
            "liquidity-pool",
            "pass",
            f"{len(cluster)} equal swing {side} at {level} within {tolerance}",
            "liquidity sweep: external pool proven",
            {"level": str(level), "swings": str(len(cluster))},
        ),
        level,
        pool_index,
    )


def rule_liquidity_sweep(
    bars: Sequence[MarketBar],
    tick_size: Decimal | None,
    params: Agent09Params,
    direction: Direction | None,
    pool_check: RuleCheck,
    level: Decimal | None,
) -> RuleCheck:
    """Step 3, sweep on a completed candle: poke within tolerance, close back.

    The third-to-last bar must pierce the pool extreme by more than zero
    but no more than ``sweep_tol_ticks``, and close back on the pool side.
    A deeper poke is a breakout, not a sweep; acceptance beyond the level
    is failure, not liquidity taken.
    """
    if pool_check.verdict == "unknown":
        return _blocked_unknown("liquidity-sweep", "pool unknown")
    if pool_check.verdict != "pass" or level is None or direction is None:
        return _blocked("liquidity-sweep", "no proven pool")
    if params.sweep_tol_ticks is None or tick_size is None:
        return _check(
            "liquidity-sweep",
            "unknown",
            "unconfigured sweep tolerance",
            "fail-closed: sweep_tol_ticks unset",
            {},
        )
    tolerance = Decimal(params.sweep_tol_ticks) * tick_size
    sweep = list(bars)[-3]
    if direction == Direction.SHORT:
        excess = sweep.high - level
        if excess <= 0:
            return _check(
                "liquidity-sweep",
                "fail",
                f"sweep high {sweep.high} never pierces pool {level}",
                "liquidity sweep: no poke beyond the pool",
                {"level": str(level)},
            )
        if excess > tolerance:
            return _check(
                "liquidity-sweep",
                "fail",
                f"poke {excess} beyond tolerance {tolerance}: breakout, not a sweep",
                "liquidity sweep: sweep tolerance broken",
                {"excess": str(excess), "tolerance": str(tolerance)},
            )
        if sweep.close >= level:
            return _check(
                "liquidity-sweep",
                "fail",
                f"sweep closes {sweep.close} at or beyond pool {level}: accepted",
                "liquidity sweep: no rejection, pattern only",
                {"level": str(level)},
            )
        return _check(
            "liquidity-sweep",
            "pass",
            f"sweep pokes {excess} beyond {level} within {tolerance}, closes back",
            "liquidity sweep: buy-side swept with rejection",
            {"excess": str(excess), "tolerance": str(tolerance)},
        )
    excess = level - sweep.low
    if excess <= 0:
        return _check(
            "liquidity-sweep",
            "fail",
            f"sweep low {sweep.low} never pierces pool {level}",
            "liquidity sweep: no poke beyond the pool",
            {"level": str(level)},
        )
    if excess > tolerance:
        return _check(
            "liquidity-sweep",
            "fail",
            f"poke {excess} beyond tolerance {tolerance}: breakout, not a sweep",
            "liquidity sweep: sweep tolerance broken",
            {"excess": str(excess), "tolerance": str(tolerance)},
        )
    if sweep.close <= level:
        return _check(
            "liquidity-sweep",
            "fail",
            f"sweep closes {sweep.close} at or beyond pool {level}: accepted",
            "liquidity sweep: no rejection, pattern only",
            {"level": str(level)},
        )
    return _check(
        "liquidity-sweep",
        "pass",
        f"sweep pokes {excess} beyond {level} within {tolerance}, closes back",
        "liquidity sweep: sell-side swept with rejection",
        {"excess": str(excess), "tolerance": str(tolerance)},
    )


def rule_displacement(
    bars: Sequence[MarketBar],
    params: Agent09Params,
    direction: Direction | None,
    sweep_check: RuleCheck,
) -> RuleCheck:
    """Step 4, displacement: a directional body clears a multiple of baseline.

    The second-to-last bar must close in the setup direction with a body
    at least ``disp_body_min_atr`` times the mean true range over the
    pre-displacement window (every range there, no assumed lookback).
    """
    if sweep_check.verdict == "unknown":
        return _blocked_unknown("displacement", "sweep unknown")
    if sweep_check.verdict != "pass" or direction is None:
        return _blocked("displacement", "no sweep")
    if params.disp_body_min_atr is None:
        return _check(
            "displacement",
            "unknown",
            "unconfigured displacement multiple",
            "fail-closed: disp_body_min_atr unset",
            {},
        )
    ordered = list(bars)
    baseline_window = ordered[:-2]
    if len(baseline_window) < 2:
        return _check(
            "displacement",
            "unknown",
            "too few bars for a displacement baseline",
            "liquidity sweep: baseline window incomplete",
            {},
        )
    baseline = average_true_range(
        baseline_window, period=len(baseline_window) - 1
    )
    if baseline is None or baseline <= 0:
        return _check(
            "displacement",
            "unknown",
            "no baseline range: displacement unmeasurable",
            "liquidity sweep: flat baseline fails closed",
            {},
        )
    push = ordered[-2]
    body = abs(push.open - push.close)
    required = params.disp_body_min_atr * baseline
    inputs = {"body": str(body), "baseline": str(baseline), "required": str(required)}
    aligned = (push.close < push.open) if direction == Direction.SHORT else (
        push.close > push.open
    )
    if not aligned:
        return _check(
            "displacement",
            "fail",
            f"displacement closes against the setup direction (body {body})",
            "liquidity sweep: no directional displacement",
            inputs,
        )
    if body < required:
        return _check(
            "displacement",
            "fail",
            f"body {body} below {required} ({params.disp_body_min_atr}x baseline)",
            "liquidity sweep: displacement too weak",
            inputs,
        )
    return _check(
        "displacement",
        "pass",
        f"directional body {body} clears {required}",
        "liquidity sweep: displacement confirmed",
        inputs,
    )


def rule_structure_shift(
    bars: Sequence[MarketBar],
    params: Agent09Params,
    direction: Direction | None,
    displacement_check: RuleCheck,
) -> RuleCheck:
    """Step 5, CHOCH/BOS per setup type: displacement breaks the far anchor.

    Short breaks the lowest pre-sweep swing low; long breaks the highest
    pre-sweep swing high. No anchor means nothing shifted — a lone
    displacement never signals.
    """
    if displacement_check.verdict == "unknown":
        return _blocked_unknown("structure-shift", "displacement unknown")
    if displacement_check.verdict != "pass" or direction is None:
        return _blocked("structure-shift", "no displacement")
    if params.swing_bars is None:
        return _check(
            "structure-shift",
            "unknown",
            "unconfigured swing window",
            "fail-closed: swing_bars unset",
            {},
        )
    ordered = list(bars)
    window = ordered[:-3]
    if len(window) < params.swing_bars * 2 + 1:
        return _check(
            "structure-shift",
            "unknown",
            "too few pre-sweep bars for the anchor window",
            "liquidity sweep: anchor window incomplete",
            {},
        )
    push_close = ordered[-2].close
    if direction == Direction.SHORT:
        anchors = swing_lows(
            window, left_bars=params.swing_bars, right_bars=params.swing_bars
        )
        if not anchors:
            return _check(
                "structure-shift",
                "fail",
                "no swing-low anchor: nothing to break",
                "liquidity sweep: lone displacement never signals",
                {},
            )
        anchor = min(point.price for point in anchors)
        if push_close < anchor:
            return _check(
                "structure-shift",
                "pass",
                f"displacement close {push_close} breaks anchor {anchor}",
                "liquidity sweep: bearish BOS confirmed",
                {"anchor": str(anchor)},
            )
        return _check(
            "structure-shift",
            "fail",
            f"displacement close {push_close} holds above anchor {anchor}",
            "liquidity sweep: no structure shift, CHOCH alone never signals",
            {"anchor": str(anchor)},
        )
    anchors = swing_highs(
        window, left_bars=params.swing_bars, right_bars=params.swing_bars
    )
    if not anchors:
        return _check(
            "structure-shift",
            "fail",
            "no swing-high anchor: nothing to break",
            "liquidity sweep: lone displacement never signals",
            {},
        )
    anchor = max(point.price for point in anchors)
    if push_close > anchor:
        return _check(
            "structure-shift",
            "pass",
            f"displacement close {push_close} breaks anchor {anchor}",
            "liquidity sweep: bullish BOS confirmed",
            {"anchor": str(anchor)},
        )
    return _check(
        "structure-shift",
        "fail",
        f"displacement close {push_close} holds below anchor {anchor}",
        "liquidity sweep: no structure shift, CHOCH alone never signals",
        {"anchor": str(anchor)},
    )


def rule_zone(
    bars: Sequence[MarketBar],
    direction: Direction | None,
    shift_check: RuleCheck,
) -> tuple[RuleCheck, Decimal | None, Decimal | None]:
    """Step 6, valid FVG and/or OB: a named zone the retest can read.

    A gap between the pre-sweep bar and the displacement bar is the FVG;
    otherwise the last opposing bar before displacement is the OB. Either
    suffices, neither may stand alone — both need the shift above. The
    FVG wins when both exist because the gap is the fresher imbalance.
    Returns the zone (low, high).
    """
    if shift_check.verdict == "unknown":
        return _blocked_unknown("order-block-zone", "shift unknown"), None, None
    if shift_check.verdict != "pass" or direction is None:
        return _blocked("order-block-zone", "no structure shift"), None, None
    ordered = list(bars)
    before, push = ordered[-4], ordered[-2]
    if direction == Direction.SHORT:
        if before.low > push.high:
            zone = (push.high, before.low)
            return (
                _check(
                    "order-block-zone",
                    "pass",
                    f"bearish FVG {zone[0]} to {zone[1]} over the sweep",
                    "liquidity sweep: valid FVG proven",
                    {"zone_low": str(zone[0]), "zone_high": str(zone[1])},
                ),
                zone[0],
                zone[1],
            )
        for bar in reversed(ordered[:-2]):
            if bar.close > bar.open:
                return (
                    _check(
                        "order-block-zone",
                        "pass",
                        f"bearish OB {bar.low} to {bar.high} before displacement",
                        "liquidity sweep: valid OB proven",
                        {"zone_low": str(bar.low), "zone_high": str(bar.high)},
                    ),
                    bar.low,
                    bar.high,
                )
    else:
        if before.high < push.low:
            zone = (before.high, push.low)
            return (
                _check(
                    "order-block-zone",
                    "pass",
                    f"bullish FVG {zone[0]} to {zone[1]} over the sweep",
                    "liquidity sweep: valid FVG proven",
                    {"zone_low": str(zone[0]), "zone_high": str(zone[1])},
                ),
                zone[0],
                zone[1],
            )
        for bar in reversed(ordered[:-2]):
            if bar.close < bar.open:
                return (
                    _check(
                        "order-block-zone",
                        "pass",
                        f"bullish OB {bar.low} to {bar.high} before displacement",
                        "liquidity sweep: valid OB proven",
                        {"zone_low": str(bar.low), "zone_high": str(bar.high)},
                    ),
                    bar.low,
                    bar.high,
                )
    return (
        _check(
            "order-block-zone",
            "fail",
            "no FVG gap and no opposing bar: no valid zone",
            "liquidity sweep: lone FVG/OB never signals",
            {},
        ),
        None,
        None,
    )


def rule_retest_confirm(
    bars: Sequence[MarketBar],
    direction: Direction | None,
    zone_check: RuleCheck,
    zone_low: Decimal | None,
    zone_high: Decimal | None,
) -> RuleCheck:
    """Step 7, retest plus entry confirmation on the last completed bar.

    The last bar must tap the zone (wick reaches in) and confirm (close
    in the setup direction). A tap without confirmation is watching, not
    a signal; confirmation without a tap is chasing.
    """
    if zone_check.verdict == "unknown":
        return _blocked_unknown("retest-confirm", "zone unknown")
    if (
        zone_check.verdict != "pass"
        or direction is None
        or zone_low is None
        or zone_high is None
    ):
        return _blocked("retest-confirm", "no valid zone")
    confirm = list(bars)[-1]
    if direction == Direction.SHORT:
        if confirm.high < zone_low:
            return _check(
                "retest-confirm",
                "fail",
                f"last high {confirm.high} never taps zone from {zone_low}",
                "liquidity sweep: no retest, no signal",
                {"zone_low": str(zone_low)},
            )
        if confirm.close >= confirm.open:
            return _check(
                "retest-confirm",
                "fail",
                "retest taps but closes against the setup direction",
                "liquidity sweep: tap without confirmation never signals",
                {},
            )
        return _check(
            "retest-confirm",
            "pass",
            f"retest taps {zone_low} and confirms down at {confirm.close}",
            "liquidity sweep: retest plus confirmation",
            {"close": str(confirm.close)},
        )
    if confirm.low > zone_high:
        return _check(
            "retest-confirm",
            "fail",
            f"last low {confirm.low} never taps zone to {zone_high}",
            "liquidity sweep: no retest, no signal",
            {"zone_high": str(zone_high)},
        )
    if confirm.close <= confirm.open:
        return _check(
            "retest-confirm",
            "fail",
            "retest taps but closes against the setup direction",
            "liquidity sweep: tap without confirmation never signals",
            {},
        )
    return _check(
        "retest-confirm",
        "pass",
        f"retest taps {zone_high} and confirms up at {confirm.close}",
        "liquidity sweep: retest plus confirmation",
        {"close": str(confirm.close)},
    )


def rule_trade_plan(
    bars: Sequence[MarketBar],
    params: Agent09Params,
    direction: Direction | None,
    confirm_check: RuleCheck,
    level: Decimal | None,
    pool_index: int | None,
) -> tuple[RuleCheck, Decimal | None, Decimal | None, Decimal | None]:
    """Step 8, invalidation, stop, target, expiry before any valid setup.

    The stop sits beyond the sweep extreme (acceptance past the pool
    invalidates); the target is the opposing pre-sweep extreme (the next
    resting liquidity); the setup must trigger within ``expiry_bars`` of
    the pool. Geometry must order, or the plan — and the setup — fails.
    Returns (check, entry, stop, target).
    """
    if confirm_check.verdict == "unknown":
        return _blocked_unknown("trade-plan", "confirmation unknown"), None, None, None
    if (
        confirm_check.verdict != "pass"
        or direction is None
        or level is None
        or pool_index is None
    ):
        return _blocked("trade-plan", "no confirmation"), None, None, None
    if params.expiry_bars is None:
        return (
            _check(
                "trade-plan",
                "unknown",
                "unconfigured setup expiry",
                "fail-closed: expiry_bars unset",
                {},
            ),
            None,
            None,
            None,
        )
    ordered = list(bars)
    age = (len(ordered) - 1) - pool_index
    if age > params.expiry_bars:
        return (
            _check(
                "trade-plan",
                "fail",
                f"pool is {age} bars old beyond expiry {params.expiry_bars}",
                "liquidity sweep: setup expired",
                {"age": str(age)},
            ),
            None,
            None,
            None,
        )
    entry = ordered[-1].close
    window = ordered[:-3]
    if direction == Direction.SHORT:
        stop = ordered[-3].high
        target = min(bar.low for bar in window)
        if not (stop > entry > target):
            return (
                _check(
                    "trade-plan",
                    "fail",
                    f"stop {stop}, entry {entry}, target {target} misordered",
                    "liquidity sweep: stop/target geometry broken",
                    {},
                ),
                None,
                None,
                None,
            )
        return (
            _check(
                "trade-plan",
                "pass",
                f"stop beyond sweep {stop}, target opposing pool {target}",
                "liquidity sweep: invalidation, stop, target, R:R set",
                {"stop": str(stop), "target": str(target)},
            ),
            entry,
            stop,
            target,
        )
    stop = ordered[-3].low
    target = max(bar.high for bar in window)
    if not (target > entry > stop):
        return (
            _check(
                "trade-plan",
                "fail",
                f"target {target}, entry {entry}, stop {stop} misordered",
                "liquidity sweep: stop/target geometry broken",
                {},
            ),
            None,
            None,
            None,
        )
    return (
        _check(
            "trade-plan",
            "pass",
            f"stop beyond sweep {stop}, target opposing pool {target}",
            "liquidity sweep: invalidation, stop, target, R:R set",
            {"stop": str(stop), "target": str(target)},
        ),
        entry,
        stop,
        target,
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent09Params
) -> tuple[
    list[RuleCheck], Direction | None, Decimal | None, Decimal | None, Decimal | None
]:
    """Compose the eight ordered steps; prices flow only when all pass."""
    ordered = list(bars)
    tick_size = Decimal(ctx.tick_size) if ctx.tick_size is not None else None
    bias, direction = rule_htf_bias(ctx)
    pool, level, pool_index = rule_liquidity_pool(ordered, tick_size, params, direction)
    sweep = rule_liquidity_sweep(ordered, tick_size, params, direction, pool, level)
    displacement = rule_displacement(ordered, params, direction, sweep)
    shift = rule_structure_shift(ordered, params, direction, displacement)
    zone, zone_low, zone_high = rule_zone(ordered, direction, shift)
    confirm = rule_retest_confirm(ordered, direction, zone, zone_low, zone_high)
    plan, entry, stop, target = rule_trade_plan(
        ordered, params, direction, confirm, level, pool_index
    )
    checks = [bias, pool, sweep, displacement, shift, zone, confirm, plan]
    if (
        direction is None
        or entry is None
        or stop is None
        or target is None
        or any(check.verdict != "pass" for check in checks)
    ):
        return checks, None, None, None, None
    return checks, direction, entry, stop, target
