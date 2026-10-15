"""Agent 6 — session-opening-range (operator 10-agent spec, agent 6 of 10)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from goldmasters_contracts import MarketBar, TrendRegime

from src.goldmasters.domain.conventions import check_bar_order
from src.goldmasters.strategies.agent_06.levels_spec import take_profits_for
from src.goldmasters.strategies.agent_06.rules import Agent06Params, run_rules
from src.goldmasters.strategies.base import (
    EligibilityRule,
    MarketContext,
    RuleCheck,
    StrategyEvaluation,
    build_evaluation,
    build_levels_evaluation,
    hash_rule_source,
)

__all__ = [
    "CODE_HASH",
    "RULE_SOURCE",
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "Agent06Params",
    "eligibility",
    "evaluate",
]

STRATEGY_ID = "session-opening-range"
STRATEGY_VERSION = "1.0.0"
RULE_SOURCE = (
    "Operator 10-agent spec 2026-10-15, Agent 6 session-opening-range: a "
    "confirmed break of a predefined session range may capture a directional "
    "move. Rules: named sessions, timezones, range duration, eligible "
    "instruments; range from in-session candles only; completed-range "
    "breakout plus confirmation, optional retest; session-end expiry, spread "
    "filters, failure handling; DST and server-time correctness."
)
CODE_HASH = hash_rule_source(RULE_SOURCE)


def _blocked(status: str, rule_id: str, reason: str) -> StrategyEvaluation:
    checks = [
        RuleCheck(
            rule_id=rule_id,
            verdict="unknown",
            inputs={},
            evidence=f"blocked: {reason}",
            reason=reason,
        )
    ]
    return build_evaluation(
        strategy_id=STRATEGY_ID,
        strategy_version=STRATEGY_VERSION,
        code_hash=CODE_HASH,
        rule_checks=checks,
        candidate_levels=None,
        limitations=[status],
    )


def eligibility(params: Agent06Params) -> EligibilityRule:
    """Matrix row for this agent; an unset min_bars still blocks at evaluate."""
    return EligibilityRule(
        strategy_id=STRATEGY_ID,
        enabled=params.enabled,
        instruments=list(params.instruments),
        timeframes=list(params.timeframes),
        regimes=list(params.regimes),
        min_bars=params.min_bars if params.min_bars is not None else 1,
    )


def evaluate(
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent06Params
) -> StrategyEvaluation:
    """Evaluate closed bars in context; thresholds ride fail-closed params."""
    ordered = list(bars)
    if check_bar_order([bar.bar_open_time for bar in ordered]) is not None:
        return _blocked("INSUFFICIENT_DATA", "input-order", "misordered bars: order preserved")
    if params.min_bars is None or len(ordered) < params.min_bars:
        return _blocked("INSUFFICIENT_DATA", "min-bars", "fewer bars than min_bars")
    if ctx.regime == TrendRegime.UNKNOWN:
        return _blocked("INSUFFICIENT_DATA", "regime", "unknown regime: no direction")
    if (
        ctx.instrument_id not in params.instruments
        or ctx.timeframe not in params.timeframes
        or ctx.regime not in params.regimes
    ):
        return _blocked("NOT_APPLICABLE", "scope", "out of this agent's scope")
    if ctx.tick_size is None:
        return _blocked("INSUFFICIENT_DATA", "precision", "unknown tick size: no levels")
    checks, direction, entry, stop = run_rules(ordered, ctx, params)
    if (
        direction is None
        or entry is None
        or stop is None
        or any(check.verdict != "pass" for check in checks)
    ):
        return build_evaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            rule_checks=checks,
            candidate_levels=None,
        )
    return build_levels_evaluation(
        strategy_id=STRATEGY_ID,
        strategy_version=STRATEGY_VERSION,
        code_hash=CODE_HASH,
        rule_checks=checks,
        direction=direction,
        entry=entry,
        stop_loss=stop,
        take_profits=take_profits_for(direction=direction, entry=entry, stop=stop),
        tick_size=Decimal(ctx.tick_size),
    )
