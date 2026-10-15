"""Agent 10 — carry-term-structure (operator 10-agent spec, agent 10 of 10)."""

from __future__ import annotations

from collections.abc import Sequence

from goldmasters_contracts import MarketBar, TrendRegime

from src.goldmasters.domain.conventions import check_bar_order
from src.goldmasters.strategies.agent_10.rules import Agent10Params, run_rules
from src.goldmasters.strategies.base import (
    EligibilityRule,
    MarketContext,
    RuleCheck,
    StrategyEvaluation,
    build_evaluation,
    hash_rule_source,
)

__all__ = [
    "CODE_HASH",
    "RULE_SOURCE",
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "Agent10Params",
    "eligibility",
    "evaluate",
]

STRATEGY_ID = "carry-term-structure"
STRATEGY_VERSION = "1.0.0"
RULE_SOURCE = (
    "Operator 10-agent spec 2026-10-15, Agent 10 carry-term-structure: "
    "financing, funding, basis, and curve information signals distinctly "
    "from price direction. One contract, three legs: forex (verified "
    "financing/forward-premium; broker swaps displayed separately, never "
    "auto-treated as carry model), crypto (verified funding/basis with "
    "timestamps plus venue/ids), oil/commodities (verified curve with "
    "expiry plus roll handling). Never infer funding or curves from spot "
    "candles; require timestamped source data plus documented calc; "
    "INSUFFICIENT_DATA or NOT_APPLICABLE when prerequisites are missing; "
    "never relabel momentum as carry. Source-data adapters are "
    "Phase 6+/operator-supplied; legs ship NOT_APPLICABLE-first."
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


def eligibility(params: Agent10Params) -> EligibilityRule:
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
    bars: Sequence[MarketBar], ctx: MarketContext, params: Agent10Params
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
    checks, direction, entry, stop, target = run_rules(ordered, ctx, params)
    assert direction is None and entry is None and stop is None and target is None
    return build_evaluation(
        strategy_id=STRATEGY_ID,
        strategy_version=STRATEGY_VERSION,
        code_hash=CODE_HASH,
        rule_checks=checks,
        candidate_levels=None,
        limitations=["NOT_APPLICABLE"],
    )
