"""Supervisor seam contract (03.5-01 Task 2): eligible_agents over all 10 rows.

No Phase 4 code lives here — no supervisor, node, or graph. This file pins
the consumption contract the Phase 4 supervisor builds on (PRD §6.4: the
supervisor selects eligible strategy agents by instrument, timeframe,
regime, and configuration): ``eligible_agents`` over the ten shipped rows
yields one verdict per agent id, and every eligible row carries the
MarketContext-relevant scope (instruments, timeframes, regimes, min_bars)
the supervisor reads. Bar count never excludes — below ``min_bars`` the
agent still reports ``INSUFFICIENT_DATA`` at evaluate time, proven through
agent 10's own ``evaluate``.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

from goldmasters_contracts import Timeframe, TrendRegime

from src.goldmasters.strategies.agent_01 import STRATEGY_ID as ID_01
from src.goldmasters.strategies.agent_02 import STRATEGY_ID as ID_02
from src.goldmasters.strategies.agent_03 import STRATEGY_ID as ID_03
from src.goldmasters.strategies.agent_04 import STRATEGY_ID as ID_04
from src.goldmasters.strategies.agent_05 import STRATEGY_ID as ID_05
from src.goldmasters.strategies.agent_06 import STRATEGY_ID as ID_06
from src.goldmasters.strategies.agent_07 import STRATEGY_ID as ID_07
from src.goldmasters.strategies.agent_08 import STRATEGY_ID as ID_08
from src.goldmasters.strategies.agent_09 import STRATEGY_ID as ID_09
from src.goldmasters.strategies.agent_10 import (
    STRATEGY_ID as ID_10,
    Agent10Params,
    eligibility as eligibility_10,
    evaluate as evaluate_10,
)
from src.goldmasters.strategies.base import (
    EligibilityRule,
    adapter_feeds_gate,
    eligible_agents,
    meets_min_bars,
)
from tests.unit.agent_fixtures import make_bar, make_ctx

EXPECTED_IDS = frozenset(
    {ID_01, ID_02, ID_03, ID_04, ID_05, ID_06, ID_07, ID_08, ID_09, ID_10}
)


def _row(
    strategy_id: str,
    *,
    enabled: bool = True,
    instruments: list[str] | None = None,
    timeframes: list[Timeframe] | None = None,
    regimes: list[TrendRegime] | None = None,
    min_bars: int = 5,
) -> EligibilityRule:
    return EligibilityRule(
        strategy_id=strategy_id,
        enabled=enabled,
        instruments=list(instruments) if instruments is not None else ["xauusd"],
        timeframes=list(timeframes) if timeframes is not None else [Timeframe.H1],
        regimes=list(regimes)
        if regimes is not None
        else [TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE],
        min_bars=min_bars,
    )


def _agent_10_row() -> EligibilityRule:
    """Agent 10's matrix row comes from its own eligibility wiring, never a literal."""
    return eligibility_10(
        Agent10Params(
            enabled=True,
            instruments=("xauusd", "eurusd", "btcusd", "usoil"),
            timeframes=(Timeframe.H1,),
            regimes=(TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE),
            min_bars=6,
            max_data_age_hours=Decimal("24"),
            min_history_points=50,
        )
    )


def _matrix() -> list[EligibilityRule]:
    """All ten shipped rows; scopes differ so each selection branch is reachable."""
    return [
        _row(ID_01),
        _row(ID_02),
        _row(ID_03, instruments=["eurusd"]),
        _row(ID_04, timeframes=[Timeframe.H4]),
        _row(ID_05, regimes=[TrendRegime.DOWNTREND]),
        _row(ID_06, enabled=False),
        _row(ID_07, min_bars=12),
        _row(ID_08),
        _row(ID_09, instruments=["xauusd", "btcusd"]),
        _agent_10_row(),
    ]


def test_matrix_covers_all_ten_approved_ids() -> None:
    matrix = _matrix()
    assert {rule.strategy_id for rule in matrix} == EXPECTED_IDS
    assert len(matrix) == 10
    assert set(eligible_agents(matrix, make_ctx())) == EXPECTED_IDS


def test_selects_per_instrument_timeframe_regime() -> None:
    matrix = _matrix()
    verdicts = eligible_agents(matrix, make_ctx())
    assert verdicts[ID_01] == "eligible"
    assert verdicts[ID_03] == "not_applicable"  # eurusd-only row, xauusd ctx
    assert verdicts[ID_04] == "not_applicable"  # H4-only row, H1 ctx
    assert verdicts[ID_05] == "not_applicable"  # downtrend-only row, uptrend ctx
    assert eligible_agents(matrix, make_ctx(instrument_id="eurusd"))[ID_03] == "eligible"
    assert eligible_agents(matrix, make_ctx(timeframe=Timeframe.H4))[ID_04] == "eligible"
    assert eligible_agents(matrix, make_ctx(regime=TrendRegime.DOWNTREND))[ID_05] == "eligible"


def test_disabled_agent_branch() -> None:
    assert eligible_agents(_matrix(), make_ctx())[ID_06] == "disabled"


def test_below_min_bars_stays_eligible_reports_insufficient() -> None:
    """Bars never exclude: the matrix still selects, evaluate reports INSUFFICIENT_DATA."""
    matrix = _matrix()
    assert eligible_agents(matrix, make_ctx(bar_count=1))[ID_07] == "eligible"
    assert meets_min_bars(next(r for r in matrix if r.strategy_id == ID_07), 1) is False
    bars = [make_bar(close="100", index=index) for index in range(3)]
    params = Agent10Params(
        enabled=True,
        instruments=("xauusd",),
        timeframes=(Timeframe.H1,),
        regimes=(TrendRegime.UPTREND,),
        min_bars=6,
        max_data_age_hours=Decimal("24"),
        min_history_points=50,
    )
    assert eligible_agents([eligibility_10(params)], make_ctx(bar_count=3))[ID_10] == "eligible"
    evaluation = evaluate_10(bars, make_ctx(bar_count=3), params)
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]


def test_seam_output_shape_matches_supervisor_consumption() -> None:
    """PRD §6.4: eligible ids plus their MarketContext-relevant scope — nothing else."""
    matrix = _matrix()
    by_id = {rule.strategy_id: rule for rule in matrix}
    verdicts = eligible_agents(matrix, make_ctx())
    assert set(verdicts.values()) <= {"eligible", "not_applicable", "disabled"}
    for strategy_id, verdict in verdicts.items():
        rule = by_id[strategy_id]
        if verdict == "eligible":
            assert rule.instruments, f"{strategy_id} carries no instrument scope"
            assert rule.timeframes, f"{strategy_id} carries no timeframe scope"
            assert rule.regimes, f"{strategy_id} carries no regime scope"
            assert rule.min_bars >= 1, f"{strategy_id} carries no bar minimum"
            assert make_ctx().instrument_id in rule.instruments
            assert make_ctx().timeframe in rule.timeframes
            assert make_ctx().regime in rule.regimes
    # Non-selected rows never reach the gate: only a setup feeds evaluate_gate.
    assert adapter_feeds_gate("NO_SETUP") is False
    assert adapter_feeds_gate("INSUFFICIENT_DATA") is False
    assert adapter_feeds_gate("NOT_APPLICABLE") is False


def test_no_phase4_code_in_seam() -> None:
    """The seam consumes eligible_agents only — no supervisor, node, or graph code."""
    lines = pathlib.Path(__file__).read_text(encoding="utf-8").splitlines()
    imports = [line for line in lines if line.startswith(("import ", "from "))]
    for forbidden in ("langgraph", "StateGraph", "Supervisor"):
        assert all(forbidden not in line for line in imports), (
            f"Phase 4 import leaked into the seam: {forbidden}"
        )
