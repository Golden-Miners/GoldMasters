"""Agent 10 rule composition: carry-term-structure legs, NOT_APPLICABLE-first.

Financing, funding, basis, and curve information signals distinctly from
price direction — so no leg reads spot candles here. The one contract
carries three legs: forex (verified financing/forward-premium), crypto
(verified funding/basis with timestamps plus venue/ids), and
oil/commodities (verified curve with expiry plus roll handling). Source-data
adapters are Phase 6+/operator-supplied, so every leg ships
NOT_APPLICABLE-first: the leg matching this instrument cites the missing
source, legs defined for other instrument classes cite not-defined scope,
and unset numerics fail closed. Nothing here ever relabels momentum as
carry. Shared math comes only from ``domain.*``, never another agent
(there is no price math to share yet).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from goldmasters_contracts import MarketBar, Timeframe, TrendRegime

from src.goldmasters.strategies.base import MarketContext, RuleCheck

#: One contract, three legs (operator 10-agent spec, agent 10 of 10).
LegId = Literal["forex-carry", "crypto-funding", "commodity-curve"]

#: Instrument classes each leg is defined for; anything else has no leg.
_FOREX_INSTRUMENTS = frozenset(
    {"eurusd", "gbpusd", "usdjpy", "audusd", "usdcad", "usdchf", "nzdusd"}
)
_CRYPTO_INSTRUMENTS = frozenset({"btcusd", "ethusd"})
_COMMODITY_INSTRUMENTS = frozenset({"xauusd", "xagusd", "usoil"})


@dataclass(frozen=True)
class Agent10Params:
    """Settings-derived row: scope lists plus operator-spec numerics."""

    enabled: bool
    instruments: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    regimes: tuple[TrendRegime, ...]
    min_bars: int | None
    max_data_age_hours: Decimal | None
    min_history_points: int | None


def leg_for_instrument(instrument_id: str) -> LegId | None:
    """Route an instrument to its defined leg; None means no leg is defined."""
    if instrument_id in _FOREX_INSTRUMENTS:
        return "forex-carry"
    if instrument_id in _CRYPTO_INSTRUMENTS:
        return "crypto-funding"
    if instrument_id in _COMMODITY_INSTRUMENTS:
        return "commodity-curve"
    return None


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


def _leg_check(leg: LegId, ctx: MarketContext, params: Agent10Params) -> RuleCheck:
    """One leg, NOT_APPLICABLE-first: never inferred from spot candles."""
    if leg_for_instrument(ctx.instrument_id) != leg:
        return _check(
            leg,
            "unknown",
            f"{leg} is not defined for {ctx.instrument_id}: out of this leg's scope",
            f"carry leg: {leg} NOT_APPLICABLE for {ctx.instrument_id}, never NO_SETUP",
            {"instrument": ctx.instrument_id},
        )
    if params.max_data_age_hours is None or params.min_history_points is None:
        return _check(
            leg,
            "unknown",
            "unconfigured carry prerequisites",
            "fail-closed: max_data_age_hours/min_history_points unset",
            {},
        )
    return _check(
        leg,
        "unknown",
        f"no verified {leg} source: financing/funding/curve adapters are operator-supplied",
        f"carry leg: {leg} NOT_APPLICABLE-first, never inferred from spot candles",
        {"instrument": ctx.instrument_id},
    )


def rule_forex_carry(ctx: MarketContext, params: Agent10Params) -> RuleCheck:
    """Forex leg: verified financing/forward-premium only (broker swaps shown separately)."""
    return _leg_check("forex-carry", ctx, params)


def rule_crypto_funding(ctx: MarketContext, params: Agent10Params) -> RuleCheck:
    """Crypto leg: verified funding/basis with timestamps plus venue/ids."""
    return _leg_check("crypto-funding", ctx, params)


def rule_commodity_curve(ctx: MarketContext, params: Agent10Params) -> RuleCheck:
    """Oil/commodities leg: verified curve with expiry plus roll handling."""
    return _leg_check("commodity-curve", ctx, params)


def run_rules(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent10Params
) -> tuple[
    list[RuleCheck], None, None, None, None
]:
    """Compose the three legs; prices flow never — every leg is unknown by construction."""
    _ = bars  # spot candles are not an input to any carry leg
    checks = [
        rule_forex_carry(ctx, params),
        rule_crypto_funding(ctx, params),
        rule_commodity_curve(ctx, params),
    ]
    return checks, None, None, None, None
