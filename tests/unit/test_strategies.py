"""Strategy interface contract (03-02 Task 3): setup + rule evidence, no strategies.

The throwaway ``_TestDoubleStrategy`` below lives in this file and is never
shipped: it proves the interface hard rule (any fail/unknown → no setup and
null levels) without creating an approved strategy package (D-3.1).
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, MarketBar, QualityStatus, Timeframe, VolumeType
from goldmasters_contracts import TrendRegime
from pydantic import ValidationError

from src.goldmasters.strategies.base import (
    MarketContext,
    RuleCheck,
    Strategy,
    StrategyEvaluation,
    build_evaluation,
    hash_rule_source,
)


def _double_ctx() -> MarketContext:
    return MarketContext(
        instrument_id="xauusd",
        provider_id="mt5",
        timeframe=Timeframe.H1,
        regime=TrendRegime.UNKNOWN,
        quality_status=QualityStatus.OK,
        quality_flags=[],
        volume_type=VolumeType.TICK,
        tick_size=None,
        contract_size=None,
        bar_count=1,
        now_utc=datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
    )


def _double_levels() -> Levels:
    """Candidate levels computed in Decimal by the test double (code computes)."""
    entry = Decimal("100.00")
    stop = Decimal("99.00")
    target = Decimal("101.00")
    risk = entry - stop
    reward = target - entry
    return Levels(
        entry=entry,
        stop_loss=stop,
        take_profits=[target],
        risk_reward=reward / risk,
    )


def _double_bars() -> list[MarketBar]:
    moment = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    return [
        MarketBar(
            instrument_id="xauusd",
            provider_id="mt5",
            provider_symbol="XAUUSD",
            timeframe=Timeframe.H1,
            bar_open_time=moment,
            bar_close_time=moment + timedelta(hours=1),
            open=Decimal("100.00"),
            high=Decimal("101.00"),
            low=Decimal("99.00"),
            close=Decimal("100.50"),
            volume=Decimal(10),
            volume_type=VolumeType.TICK,
            retrieved_at=moment + timedelta(hours=1),
            source_timezone="UTC",
            quality_status=QualityStatus.OK,
        )
    ]


class _TestDoubleStrategy:
    """Throwaway test double (test file only, never shipped as a strategy)."""

    STRATEGY_ID = "test-double"
    STRATEGY_VERSION = "0.1.0"
    CODE_HASH = hash_rule_source("test-double rules: pass/fail/unknown by constructor flag")

    def __init__(self, verdicts: Sequence[str]) -> None:
        self._verdicts = list(verdicts)

    def evaluate(self, bars: Sequence[MarketBar], ctx: MarketContext) -> StrategyEvaluation:
        checks = [
            RuleCheck(
                rule_id=f"rule-{i + 1}",
                verdict=verdict,  # type: ignore[arg-type]
                inputs={"bars": str(len(bars)), "regime": ctx.regime.value},
                evidence=f"double evidence for rule-{i + 1}",
                reason=f"double verdict {verdict}",
            )
            for i, verdict in enumerate(self._verdicts)
        ]
        levels = _double_levels() if all(v == "pass" for v in self._verdicts) else None
        return build_evaluation(
            strategy_id=self.STRATEGY_ID,
            strategy_version=self.STRATEGY_VERSION,
            code_hash=self.CODE_HASH,
            rule_checks=checks,
            candidate_levels=levels,
        )


def test_double_satisfies_strategy_protocol() -> None:
    assert isinstance(_TestDoubleStrategy(["pass"]), Strategy)


def test_all_pass_yields_setup_with_levels_and_stamp() -> None:
    evaluation = _TestDoubleStrategy(["pass", "pass"]).evaluate(_double_bars(), _double_ctx())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == "test-double"
    assert evaluation.strategy_version == "0.1.0"
    assert evaluation.code_hash == _TestDoubleStrategy.CODE_HASH
    assert [c.rule_id for c in evaluation.rule_checks] == ["rule-1", "rule-2"]
    assert all(c.verdict == "pass" for c in evaluation.rule_checks)


def test_single_fail_yields_no_setup_and_null_levels() -> None:
    evaluation = _TestDoubleStrategy(["pass", "fail"]).evaluate(_double_bars(), _double_ctx())
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert evaluation.rule_checks[1].verdict == "fail"


def test_unknown_rule_yields_no_setup_and_null_levels() -> None:
    evaluation = _TestDoubleStrategy(["pass", "unknown"]).evaluate(_double_bars(), _double_ctx())
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None


def test_interface_rejects_levels_on_failed_rule() -> None:
    """T-03-06: the no-escape clause is enforced on construction, not convention."""
    check = RuleCheck(
        rule_id="rule-1",
        verdict="fail",
        evidence="e",
        reason="r",
    )
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0.0",
            code_hash="h",
            setup_found=True,
            rule_checks=[check],
            candidate_levels=_double_levels(),
        )
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0.0",
            code_hash="h",
            setup_found=False,
            rule_checks=[check],
            candidate_levels=_double_levels(),
        )
    with pytest.raises(ValidationError, match="must carry candidate levels"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0.0",
            code_hash="h",
            setup_found=True,
            rule_checks=[RuleCheck(rule_id="rule-1", verdict="pass", evidence="e", reason="r")],
            candidate_levels=None,
        )


def test_evaluation_rejects_bad_version_and_empty_checks() -> None:
    good = RuleCheck(rule_id="rule-1", verdict="pass", evidence="e", reason="r")
    with pytest.raises(ValidationError, match="strategy_version"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0",
            code_hash="h",
            setup_found=False,
            rule_checks=[good],
        )
    with pytest.raises(ValidationError, match="rule_checks"):
        StrategyEvaluation(
            strategy_id="x",
            strategy_version="1.0.0",
            code_hash="h",
            setup_found=False,
            rule_checks=[],
        )


# The exact approved-agent set. Empty in phase 3.1 (framework only); each
# agent phase extends this set as it ships its package.
EXPECTED_APPROVED_STRATEGIES: frozenset[str] = frozenset()


def test_strategy_registry_lists_approved_agents() -> None:
    """D-3.1: the registry test names exactly the approved agent packages so far."""
    strategies_dir = (
        pathlib.Path(__file__).resolve().parents[2] / "src" / "goldmasters" / "strategies"
    )
    approved = frozenset(
        entry.name
        for entry in strategies_dir.iterdir()
        if entry.is_dir() and (entry / "__init__.py").is_file()
    )
    assert approved == EXPECTED_APPROVED_STRATEGIES
