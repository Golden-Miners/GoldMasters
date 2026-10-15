"""Risk-gate contract (03-03 Tasks 2-3): block with reasons, sole path to TRADE.

Covers: ordering / limits / quality / evidence blocks each record reasons;
``trade_eligible_levels`` is the sole path to TRADE-eligible levels (T-03-07);
conflicts are preserved, never reconciled; the Monitoring role shape carries
no trading-recommendation field (criterion 6, T-03-09).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from goldmasters_contracts import (
    AgentRunStatus,
    ContractModel,
    Decision,
    DecisionRecord,
    Direction,
    EvidenceStatus,
    Levels,
    QualityStatus,
    Timeframe,
    TrendRegime,
)
from pydantic import ValidationError

from src.goldmasters.risk.gate import GateVerdict, evaluate_gate, trade_eligible_levels
from src.goldmasters.strategies.base import RuleCheck, build_evaluation

NOW = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
MIN_RR = Decimal("1.5")
MAX_RISK = Decimal("2")
IDEA_RISK = Decimal("1")
HEALTHY_EVIDENCE = {"bars": EvidenceStatus.VALID, "precision": EvidenceStatus.VALID}


def _passing_levels() -> Levels:
    return Levels(
        entry=Decimal("100.00"),
        stop_loss=Decimal("99.00"),
        take_profits=[Decimal("102.00")],
        risk_reward=Decimal("2"),
    )


def _evaluation(levels: Levels | None = None) -> Any:
    check = RuleCheck(rule_id="rule-1", verdict="pass", evidence="e", reason="r")
    return build_evaluation(
        strategy_id="test-double",
        strategy_version="0.1.0",
        code_hash="h",
        rule_checks=[check],
        candidate_levels=_passing_levels() if levels is None else levels,
    )


def _gate_kwargs(**overrides: Any) -> Any:
    kwargs: dict[str, Any] = {
        "evaluation": _evaluation(),
        "direction": Direction.LONG,
        "regime": TrendRegime.UPTREND,
        "quality_status": QualityStatus.OK,
        "quality_flags": [],
        "evidence": dict(HEALTHY_EVIDENCE),
        "min_risk_reward_ratio": MIN_RR,
        "max_risk_percent_per_idea": MAX_RISK,
        "risk_percent_for_idea": IDEA_RISK,
    }
    kwargs.update(overrides)
    return kwargs


def test_pass_carries_levels_and_no_reasons() -> None:
    verdict = evaluate_gate(**_gate_kwargs())
    assert verdict.passed is True
    assert verdict.levels == _passing_levels()
    assert verdict.reasons_for_rejection == []


def test_ordering_violation_blocks_with_reason() -> None:
    bad = Levels(
        entry=Decimal("100.00"),
        stop_loss=Decimal("101.00"),  # wrong side for long
        take_profits=[Decimal("102.00")],
        risk_reward=Decimal("2"),
    )
    verdict = evaluate_gate(**_gate_kwargs(evaluation=_evaluation(levels=bad)))
    assert verdict.passed is False
    assert verdict.levels is None
    assert any("ordering" in reason for reason in verdict.reasons_for_rejection)


def test_unset_risk_policy_blocks_fail_closed() -> None:
    verdict = evaluate_gate(**_gate_kwargs(min_risk_reward_ratio=None))
    assert verdict.passed is False
    assert any("MIN_RISK_REWARD_RATIO" in reason for reason in verdict.reasons_for_rejection)
    verdict = evaluate_gate(**_gate_kwargs(max_risk_percent_per_idea=None))
    assert verdict.passed is False
    assert any("MAX_RISK_PERCENT_PER_IDEA" in reason for reason in verdict.reasons_for_rejection)


def test_risk_limit_breach_blocks() -> None:
    verdict = evaluate_gate(**_gate_kwargs(min_risk_reward_ratio=Decimal("3")))
    assert verdict.passed is False
    assert any("below configured minimum" in reason for reason in verdict.reasons_for_rejection)
    verdict = evaluate_gate(**_gate_kwargs(risk_percent_for_idea=Decimal("5")))
    assert verdict.passed is False
    assert any("exceeds configured maximum" in reason for reason in verdict.reasons_for_rejection)
    verdict = evaluate_gate(**_gate_kwargs(risk_percent_for_idea=None))
    assert verdict.passed is False
    assert any("unknown" in reason for reason in verdict.reasons_for_rejection)


def test_flagged_quality_blocks() -> None:
    verdict = evaluate_gate(**_gate_kwargs(quality_status=QualityStatus.STALE))
    assert verdict.passed is False
    assert any("data quality" in reason for reason in verdict.reasons_for_rejection)
    verdict = evaluate_gate(
        **_gate_kwargs(quality_status=QualityStatus.OK, quality_flags=[QualityStatus.GAP])
    )
    assert verdict.passed is False


def test_incomplete_evidence_blocks() -> None:
    verdict = evaluate_gate(**_gate_kwargs(evidence=None))
    assert verdict.passed is False
    assert any("evidence" in reason for reason in verdict.reasons_for_rejection)
    verdict = evaluate_gate(**_gate_kwargs(evidence={"bars": EvidenceStatus.STALE}))
    assert verdict.passed is False
    assert verdict.reasons_for_rejection == ["evidence not valid: bars"]


def test_unknown_regime_and_no_setup_block() -> None:
    verdict = evaluate_gate(**_gate_kwargs(regime=TrendRegime.UNKNOWN))
    assert verdict.passed is False
    assert any("unknown regime" in reason for reason in verdict.reasons_for_rejection)
    failing = RuleCheck(rule_id="rule-1", verdict="fail", evidence="e", reason="r")
    no_setup = build_evaluation(
        strategy_id="x", strategy_version="1.0.0", code_hash="h", rule_checks=[failing]
    )
    verdict = evaluate_gate(**_gate_kwargs(evaluation=no_setup))
    assert verdict.passed is False
    assert any("no setup" in reason for reason in verdict.reasons_for_rejection)


def test_conflicts_preserved_never_reconciled() -> None:
    verdict = evaluate_gate(**_gate_kwargs(conflicts=["trend says up, news says down"]))
    assert verdict.passed is True
    assert verdict.conflicts == ["trend says up, news says down"]


def test_gate_verdict_invariants_enforced() -> None:
    with pytest.raises(ValidationError, match="blocked verdict"):
        GateVerdict(passed=False, reasons_for_rejection=[])
    with pytest.raises(ValidationError, match="blocked verdict"):
        GateVerdict(passed=False, reasons_for_rejection=["r"], levels=_passing_levels())
    with pytest.raises(ValidationError, match="passed verdict"):
        GateVerdict(passed=True, levels=_passing_levels(), reasons_for_rejection=["r"])


def _trade_record(levels: Levels) -> DecisionRecord:
    return DecisionRecord(
        decision_id="dec_12345678-1234-5678-1234-567812345678",
        run_id="run_12345678-1234-5678-1234-567812345678",
        instrument_id="xauusd",
        timeframe=Timeframe.H1,
        decision=Decision.TRADE,
        direction=Direction.LONG,
        created_at=NOW,
        data_as_of=NOW,
        strategy_id="test-double",
        strategy_version="0.1.0",
        entry=levels.entry,
        stop_loss=levels.stop_loss,
        take_profits=list(levels.take_profits),
        risk_reward=levels.risk_reward,
        thesis="gate-verified candidate",
        data_quality_status=QualityStatus.OK,
        agent_statuses={"risk_gate": AgentRunStatus.OK},
    )


def test_bypass_blocked_levels_cannot_become_trade() -> None:
    """T-03-07: the gate is the sole path — a blocked verdict yields null levels,
    and a TRADE record without complete levels is rejected by the contract."""
    blocked = evaluate_gate(**_gate_kwargs(quality_status=QualityStatus.STALE))
    assert trade_eligible_levels(blocked) is None
    with pytest.raises(ValidationError, match="must carry all validated levels"):
        DecisionRecord(
            decision_id="dec_12345678-1234-5678-1234-567812345678",
            run_id="run_12345678-1234-5678-1234-567812345678",
            instrument_id="xauusd",
            timeframe=Timeframe.H1,
            decision=Decision.TRADE,
            direction=Direction.LONG,
            created_at=NOW,
            data_as_of=NOW,
            thesis="unvalidated levels",
            data_quality_status=QualityStatus.STALE,
        )


def test_passed_levels_reach_trade_record() -> None:
    verdict = evaluate_gate(**_gate_kwargs())
    levels = trade_eligible_levels(verdict)
    assert levels is not None
    record = _trade_record(levels)
    assert record.decision == Decision.TRADE
    assert record.validated_levels() == levels


class _MonitoringReportShape(ContractModel):
    """Test-only mirror of the docs/roles.md Monitoring row: health + activity,
    never a trading recommendation (criterion 6, T-03-09)."""

    monitor_id: str
    observed_at: str
    watched: list[str]
    health: str
    limitations: list[str]


def test_monitoring_shape_carries_no_recommendation() -> None:
    fields = set(_MonitoringReportShape.model_fields)
    assert not ({"recommendation", "signal", "trade", "decision", "direction", "levels"} & fields)
    report = _MonitoringReportShape(
        monitor_id="monitoring",
        observed_at="2026-01-06T12:00:00Z",
        watched=["feed-heartbeat"],
        health="ok",
        limitations=[],
    )
    assert report.health == "ok"
    with pytest.raises(ValidationError):
        _MonitoringReportShape(
            monitor_id="monitoring",
            observed_at="2026-01-06T12:00:00Z",
            watched=[],
            health="ok",
            limitations=[],
            recommendation="buy",  # type: ignore[call-arg]
        )
