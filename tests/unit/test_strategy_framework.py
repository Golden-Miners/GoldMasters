"""Strategy framework contract (03.1-01 Task 1): ctx, adapter, matrix, protocol.

Covers the 3.1 extension of ``strategies/base.py``: the ``MarketContext``
input, the 4-state status adapter with its locked gate-input table, the
eligibility matrix (empty instruments means none), the ``evaluate(bars,
ctx)`` protocol, and a validator-untouched test proving failed checks still
raise on construction (``test_strategies.py`` cheat-rejection precedent).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from goldmasters_contracts import (
    AgentRunStatus,
    Direction,
    MarketBar,
    QualityStatus,
    Timeframe,
    TrendRegime,
    VolumeType,
)
from pydantic import ValidationError

from src.goldmasters.strategies.base import (
    AdapterStatus,
    EligibilityRule,
    MarketContext,
    RuleCheck,
    Strategy,
    StrategyEvaluation,
    adapter_feeds_gate,
    adapter_run_status,
    build_adapter_evaluation,
    build_evaluation,
    build_levels_evaluation,
    eligible_agents,
    hash_rule_source,
    meets_min_bars,
)


def _double_ctx(**overrides: object) -> MarketContext:
    fields: dict[str, object] = {
        "instrument_id": "xauusd",
        "provider_id": "mt5",
        "timeframe": Timeframe.H1,
        "regime": TrendRegime.UPTREND,
        "quality_status": QualityStatus.OK,
        "quality_flags": [],
        "volume_type": VolumeType.TICK,
        "tick_size": None,
        "contract_size": None,
        "bar_count": 10,
        "now_utc": datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
    }
    fields.update(overrides)
    return MarketContext(**fields)  # type: ignore[arg-type]


def _passing_checks() -> list[RuleCheck]:
    return [
        RuleCheck(rule_id="rule-1", verdict="pass", evidence="e", reason="r"),
    ]


def _double_rule(strategy_id: str = "framework-double") -> EligibilityRule:
    return EligibilityRule(
        strategy_id=strategy_id,
        enabled=True,
        instruments=["xauusd"],
        timeframes=[Timeframe.H1],
        regimes=[TrendRegime.UPTREND],
        min_bars=5,
    )


def test_market_context_carries_no_price_data() -> None:
    ctx = _double_ctx()
    assert "price" not in MarketContext.model_fields
    assert "volume" not in {name for name in MarketContext.model_fields if name != "volume_type"}
    assert ctx.bar_count == 10
    assert ctx.tick_size is None  # None means skip alignment, never a default


def test_adapter_maps_each_status_per_locked_table() -> None:
    assert adapter_run_status("SETUP_FOUND") == AgentRunStatus.OK
    assert adapter_run_status("NO_SETUP") == AgentRunStatus.NO_SETUP
    assert adapter_run_status("INSUFFICIENT_DATA") == AgentRunStatus.INSUFFICIENT_DATA
    assert adapter_run_status("NOT_APPLICABLE") == AgentRunStatus.SKIPPED


def test_adapter_gate_input_only_for_setup_found() -> None:
    assert adapter_feeds_gate("SETUP_FOUND") is True
    assert adapter_feeds_gate("NO_SETUP") is False
    assert adapter_feeds_gate("INSUFFICIENT_DATA") is False
    assert adapter_feeds_gate("NOT_APPLICABLE") is False


def test_not_applicable_builds_skipped_no_levels_no_gate() -> None:
    status: AdapterStatus = "NOT_APPLICABLE"
    evaluation, run_status = build_adapter_evaluation(
        status=status,
        strategy_id="s",
        strategy_version="1.0.0",
        code_hash="h",
        rule_checks=_passing_checks(),
        limitations=["out of scope: short leg not defined"],
    )
    assert run_status == AgentRunStatus.SKIPPED
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert adapter_feeds_gate(status) is False


def test_non_setup_statuses_cannot_carry_levels() -> None:
    from src.goldmasters.risk.levels import build_candidate_levels

    levels = build_candidate_levels(
        direction=Direction.LONG,
        rule_checks=_passing_checks(),
        entry=Decimal("100.00"),
        stop_loss=Decimal("99.00"),
        take_profits=[Decimal("101.00")],
        tick_size=Decimal("0.01"),
    )
    assert levels is not None
    for status in ("NO_SETUP", "INSUFFICIENT_DATA", "NOT_APPLICABLE"):
        evaluation, _ = build_adapter_evaluation(
            status=status,  # type: ignore[arg-type]
            strategy_id="s",
            strategy_version="1.0.0",
            code_hash="h",
            rule_checks=_passing_checks(),
            candidate_levels=levels,
        )
        assert evaluation.setup_found is False
        assert evaluation.candidate_levels is None


def test_matrix_selects_on_enable_instrument_timeframe_regime() -> None:
    matrix = [_double_rule("s")]
    assert eligible_agents(matrix, _double_ctx()) == {"s": "eligible"}
    disabled = _double_rule("s").model_copy(update={"enabled": False})
    assert eligible_agents([disabled], _double_ctx()) == {"s": "disabled"}
    assert eligible_agents(matrix, _double_ctx(instrument_id="eurusd")) == {
        "s": "not_applicable"
    }
    assert eligible_agents(matrix, _double_ctx(timeframe=Timeframe.H4)) == {
        "s": "not_applicable"
    }
    assert eligible_agents(matrix, _double_ctx(regime=TrendRegime.RANGE)) == {
        "s": "not_applicable"
    }


def test_matrix_empty_instruments_means_none_never_all() -> None:
    rule = _double_rule("s").model_copy(update={"instruments": []})
    assert eligible_agents([rule], _double_ctx()) == {"s": "not_applicable"}


def test_matrix_bars_never_exclude_below_min_is_insufficient_data() -> None:
    rule = _double_rule("s")
    assert eligible_agents([rule], _double_ctx(bar_count=1)) == {"s": "eligible"}
    assert meets_min_bars(rule, 5) is True
    assert meets_min_bars(rule, 4) is False


def test_protocol_requires_bars_and_ctx() -> None:
    class _Double:
        STRATEGY_ID = "d"
        STRATEGY_VERSION = "0.1.0"
        CODE_HASH = hash_rule_source("d")

        def evaluate(self, bars: list[MarketBar], ctx: MarketContext) -> StrategyEvaluation:
            return build_evaluation(
                strategy_id=self.STRATEGY_ID,
                strategy_version=self.STRATEGY_VERSION,
                code_hash=self.CODE_HASH,
                rule_checks=_passing_checks(),
            )

    assert isinstance(_Double(), Strategy)


def test_levels_build_path_routes_through_risk_levels() -> None:
    evaluation = build_levels_evaluation(
        strategy_id="s",
        strategy_version="1.0.0",
        code_hash="h",
        rule_checks=_passing_checks(),
        direction=Direction.LONG,
        entry=Decimal("100.00"),
        stop_loss=Decimal("99.00"),
        take_profits=[Decimal("101.00")],
        tick_size=Decimal("0.01"),
    )
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.candidate_levels.entry == Decimal("100.00")


def test_validator_untouched_failed_checks_still_raise() -> None:
    """The no-escape validator keeps byte-identical behavior under the new protocol."""
    check = RuleCheck(rule_id="rule-1", verdict="fail", evidence="e", reason="r")
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0.0",
            code_hash="h",
            setup_found=True,
            rule_checks=[check],
            candidate_levels=None,
        )
