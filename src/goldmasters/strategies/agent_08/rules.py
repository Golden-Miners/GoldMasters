"""Agent 8 rule composition: session VWAP first, deviation bands second.

Session-VWAP deviations may revert under specified intraday conditions — so
the session anchor and the volume source are proven before any band is read,
and missing or unsuitable volume rejects (a tick-volume VWAP is labelled
tick-volume, never centralized). Missing numerics yield ``unknown``
(fail-closed). Independent config and evaluation from Agent 7: shared reads
come only from ``domain.*``, never from another agent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfoNotFoundError

from goldmasters_contracts import (
    Direction,
    MarketBar,
    Timeframe,
    TrendRegime,
    VolumeType,
)

from src.goldmasters.domain.conventions import session_local_date
from src.goldmasters.strategies.base import MarketContext, RuleCheck


@dataclass(frozen=True)
class Agent08Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    session_name: str | None
    session_tz: str | None
    band_sigmas: Decimal | None
    min_volume_bars: int | None


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


def session_vwap(bars: Sequence[MarketBar]) -> tuple[Decimal | None, Decimal | None]:
    """Session VWAP and its volume-weighted dispersion over the given bars.

    Typical price carries the bar range (high/low/close); weights are the bar
    volumes. ``None`` when the volume is missing (no nonzero prints, or an
    unknown print), so the caller fails closed instead of dividing by zero.
    """
    pairs: list[tuple[Decimal, Decimal]] = []
    for bar in list(bars):
        if bar.volume is None:
            return None, None
        pairs.append((_typical(bar), bar.volume))
    weighted = sum((price * volume for price, volume in pairs), Decimal(0))
    total = sum((volume for _, volume in pairs), Decimal(0))
    if total <= 0:
        return None, None
    vwap = weighted / total
    variance = (
        sum(volume * (price - vwap) ** 2 for price, volume in pairs) / total
    )
    return vwap, variance.sqrt()


def _typical(bar: MarketBar) -> Decimal:
    return (bar.high + bar.low + bar.close) / Decimal(3)


def rule_session_scope(bars: Sequence[MarketBar], params: Agent08Params) -> RuleCheck:
    """Session anchor in its timezone; VWAP resets every local session day.

    The zoneinfo database converts each instant, so DST shifts never smear
    one session's VWAP into the next; bars from two local days reject.
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
            f"bars span {len(days)} local session days: VWAP anchor expired",
            "vwap reversion: VWAP resets every session, stale anchor rejects",
            {"session": params.session_name, "tz": params.session_tz},
        )
    return _check(
        "session-scope",
        "pass",
        f"all bars in session {params.session_name} day {days.pop()}",
        "vwap reversion: single-session anchor only",
        {"session": params.session_name, "tz": params.session_tz},
    )


def rule_range_gate(ctx: MarketContext) -> RuleCheck:
    """Range/reversion regime filter: trends never revert to VWAP here."""
    if ctx.regime == TrendRegime.RANGE:
        return _check(
            "range-regime-gate",
            "pass",
            "regime is range-bound: VWAP reversion may apply",
            "vwap reversion: regime filter satisfied",
            {"regime": ctx.regime.value},
        )
    return _check(
        "range-regime-gate",
        "fail",
        f"regime {ctx.regime.value} is not range-bound: no reversion read",
        "vwap reversion: trend regime rejects",
        {"regime": ctx.regime.value},
    )


def rule_volume_source(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent08Params
) -> RuleCheck:
    """Documented volume source with a like-for-like provenance check.

    The evidence names the actual unanimous source — tick-volume VWAP stays
    tick-volume, never relabelled centralized. Mixed types, unknown sources,
    or a context mismatch reject; too few nonzero prints stay unknown
    (missing volume, fail-closed).
    """
    if params.min_volume_bars is None:
        return _check(
            "volume-source",
            "unknown",
            "unconfigured minimum volume bars",
            "fail-closed: min_volume_bars unset",
            {},
        )
    ordered = list(bars)
    sources = {bar.volume_type for bar in ordered}
    if len(sources) > 1:
        return _check(
            "volume-source",
            "fail",
            f"mixed volume types {[s.value for s in sources]}: unsuitable volume",
            "vwap reversion: reject on unsuitable volume",
            {},
        )
    source = sources.pop()
    label = {
        VolumeType.TICK: "tick-volume",
        VolumeType.EXCHANGE: "exchange-volume",
        VolumeType.BROKER: "broker-volume",
    }.get(source)
    if label is None:
        return _check(
            "volume-source",
            "fail",
            f"volume source {source.value}: no usable volume",
            "vwap reversion: reject on missing volume source",
            {},
        )
    if source != ctx.volume_type:
        return _check(
            "volume-source",
            "fail",
            f"bar volume {source.value} differs from context {ctx.volume_type.value}",
            "vwap reversion: provenance mismatch, never relabelled",
            {},
        )
    nonzero = sum(1 for bar in ordered if bar.volume is not None and bar.volume > 0)
    if nonzero < params.min_volume_bars:
        return _check(
            "volume-source",
            "unknown",
            f"{nonzero} nonzero-volume bars below {params.min_volume_bars}",
            "vwap reversion: missing volume fails closed",
            {},
        )
    return _check(
        "volume-source",
        "pass",
        f"{label} VWAP over {nonzero} nonzero-volume bars",
        "vwap reversion: documented volume source proven",
        {"source": label, "bars": str(nonzero)},
    )


def rule_vwap_extension(
    bars: Sequence[MarketBar], params: Agent08Params
) -> tuple[RuleCheck, Direction | None, Decimal | None]:
    """Deviation bands around session VWAP; direction points back to VWAP.

    The deviation reads the last close (the entry price), so the reversion
    target always sits on the correct side of entry. Returns VWAP as target.
    """
    if params.band_sigmas is None:
        return (
            _check(
                "vwap-extension",
                "unknown",
                "unconfigured band width",
                "fail-closed: band_sigmas unset",
                {},
            ),
            None,
            None,
        )
    vwap, sigma = session_vwap(list(bars))
    if vwap is None or sigma is None:
        return (
            _check(
                "vwap-extension",
                "unknown",
                "VWAP indeterminate without nonzero volume",
                "missing volume fails closed",
                {},
            ),
            None,
            None,
        )
    if sigma == 0:
        return (
            _check(
                "vwap-extension",
                "fail",
                f"no dispersion around VWAP {vwap}: flat, not extended",
                "vwap reversion: no deviation from VWAP",
                {"vwap": str(vwap)},
            ),
            None,
            None,
        )
    ordered = list(bars)
    deviation = ordered[-1].close - vwap
    band = params.band_sigmas * sigma
    inputs = {"vwap": str(vwap), "band": str(band), "deviation": str(deviation)}
    direction = Direction.SHORT if deviation > 0 else Direction.LONG
    if abs(deviation) >= band:
        side = "above" if deviation > 0 else "below"
        return (
            _check(
                "vwap-extension",
                "pass",
                f"close {deviation} {side} VWAP {vwap} clears band {band}",
                "vwap reversion: deviation band broken",
                inputs,
            ),
            direction,
            vwap,
        )
    return (
        _check(
            "vwap-extension",
            "fail",
            f"close {deviation} from VWAP {vwap} inside band {band}",
            "vwap reversion: no band deviation",
            inputs,
        ),
        None,
        None,
    )


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent08Params
) -> tuple[
    list[RuleCheck], Direction | None, Decimal | None, Decimal | None, Decimal | None
]:
    """Compose the four operator rules; stop is structural, target is VWAP."""
    ordered = list(bars)
    scope = rule_session_scope(ordered, params)
    gate = rule_range_gate(ctx)
    volume = rule_volume_source(ordered, ctx, params)
    extension, direction, vwap = rule_vwap_extension(ordered, params)
    checks = [scope, gate, volume, extension]
    if direction is None or vwap is None:
        return checks, None, None, None, None
    entry = ordered[-1].close
    lows = [bar.low for bar in ordered]
    highs = [bar.high for bar in ordered]
    stop = min(lows) if direction == Direction.LONG else max(highs)
    return checks, direction, entry, stop, vwap
