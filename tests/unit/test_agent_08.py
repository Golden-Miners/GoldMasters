"""Agent 8 vwap-reversion: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime, VolumeType
from pydantic import ValidationError

from src.goldmasters.strategies.agent_08 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent08Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_08.rules import session_vwap
from src.goldmasters.strategies.base import (
    RuleCheck,
    StrategyEvaluation,
    eligible_agents,
)
from tests.unit.agent_fixtures import (
    assert_decimal_only,
    bars_from_closes,
    make_bar,
    make_ctx,
)

FIXTURE_SHORT = ["100", "100", "100", "100", "100", "115", "114"]
FIXTURE_LONG = ["100", "100", "100", "100", "100", "85", "86"]
FIXTURE_FLAT = ["100"] * 7


def _params(**overrides: object) -> Agent08Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE),
        "min_bars": 6,
        "session_name": "london",
        "session_tz": "UTC",
        "band_sigmas": Decimal("1.0"),
        "min_volume_bars": 5,
    }
    fields.update(overrides)
    return Agent08Params(**fields)  # type: ignore[arg-type]


def _range_ctx(**overrides: object) -> object:
    fields: dict[str, object] = {"regime": TrendRegime.RANGE}
    fields.update(overrides)
    return make_ctx(**fields)  # type: ignore[arg-type]


def _bars_at(closes: list[str], start: datetime) -> list:
    """FIXTURE closes on hourly bars starting at an explicit UTC open."""
    bars = []
    previous: str | None = None
    for index, close in enumerate(closes):
        moment = start + timedelta(hours=index)
        bar = make_bar(close=close, open_=previous or close, index=0)
        bars.append(
            bar.model_copy(
                update={
                    "bar_open_time": moment,
                    "bar_close_time": moment + timedelta(hours=1),
                    "retrieved_at": moment + timedelta(hours=1),
                }
            )
        )
        previous = close
    return bars


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_LONG), _range_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "vwap-reversion"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)
    volume = next(check for check in evaluation.rule_checks if check.rule_id == "volume-source")
    assert "tick-volume VWAP" in volume.evidence
    assert "centralized" not in volume.evidence and "exchange-volume" not in volume.evidence


def test_all_pass_short_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_SHORT), _range_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None


@pytest.mark.parametrize(
    ("label", "closes", "ctx_regime"),
    [
        ("scope", FIXTURE_SHORT, TrendRegime.RANGE),
        ("gate", FIXTURE_SHORT, TrendRegime.UPTREND),
        ("volume", FIXTURE_SHORT, TrendRegime.RANGE),
        ("extension", FIXTURE_FLAT, TrendRegime.RANGE),
    ],
)
def test_each_rule_fail_yields_no_setup(label: str, closes: list[str], ctx_regime: object) -> None:
    if label == "scope":
        bars = _bars_at(closes, datetime(2026, 1, 6, 20, 0, tzinfo=UTC))
    elif label == "volume":
        bars = bars_from_closes(closes)
        bars[0] = bars[0].model_copy(update={"volume_type": VolumeType.EXCHANGE})
    else:
        bars = bars_from_closes(closes)
    evaluation = evaluate(
        bars, make_ctx(regime=ctx_regime), _params()  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "fail" for check in evaluation.rule_checks)


def test_unknown_verdict_yields_no_setup() -> None:
    zeroed = [
        bar.model_copy(update={"volume": Decimal(0)})
        for bar in bars_from_closes(FIXTURE_SHORT)
    ]
    evaluation = evaluate(zeroed, _range_ctx(), _params())  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(bars_from_closes(FIXTURE_SHORT), _range_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="vwap-extension", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


@pytest.mark.parametrize("regime", [TrendRegime.RANGE])
def test_insufficient_data_branches(regime: TrendRegime) -> None:
    bars = bars_from_closes(FIXTURE_SHORT)
    short = evaluate(bars[:3], make_ctx(regime=regime), _params())
    assert short.setup_found is False
    assert short.limitations == ["INSUFFICIENT_DATA"]
    no_tick = evaluate(bars, make_ctx(regime=regime, tick_size=None), _params())
    assert no_tick.setup_found is False
    assert no_tick.limitations == ["INSUFFICIENT_DATA"]
    from goldmasters_contracts import TrendRegime as TR

    unknown_regime = evaluate(bars, make_ctx(regime=TR.UNKNOWN), _params())
    assert unknown_regime.setup_found is False
    assert unknown_regime.limitations == ["INSUFFICIENT_DATA"]


def test_not_applicable_scope_branch() -> None:
    bars = bars_from_closes(FIXTURE_SHORT)
    out = evaluate(bars, make_ctx(instrument_id="eurusd", regime=TrendRegime.RANGE), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(instrument_id="eurusd"))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], _range_ctx())[STRATEGY_ID] == "eligible"  # type: ignore[arg-type]


def test_no_look_ahead() -> None:
    bars = bars_from_closes(FIXTURE_SHORT)
    params = _params()
    ctx = _range_ctx()
    prefix = bars[:6]
    before = evaluate(prefix, ctx, params)  # type: ignore[arg-type]
    future = make_bar(close="130", index=6)
    assert evaluate(prefix, ctx, params) == before  # type: ignore[arg-type]
    assert session_vwap(prefix) == session_vwap([*prefix, future][:6])


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_SHORT)
    assert evaluate(bars, _range_ctx(), _params()) == evaluate(  # type: ignore[arg-type]
        bars, _range_ctx(), _params()
    )


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_08"))


def test_independent_from_agent_07() -> None:
    """Agent 8 shares math only through domain.* — never another agent's package."""
    package = pathlib.Path("src/goldmasters/strategies/agent_08")
    for source_file in sorted(package.glob("*.py")):
        text = source_file.read_text(encoding="utf-8")
        assert "agent_07" not in text, f"cross-agent reference in {source_file.name}"
        assert "agent_06" not in text, f"cross-agent reference in {source_file.name}"


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = bars_from_closes(FIXTURE_SHORT)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, _range_ctx(), _params())  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize(
    "field",
    ["session_name", "session_tz", "band_sigmas", "min_volume_bars"],
)
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(
        bars_from_closes(FIXTURE_SHORT), _range_ctx(), _params(**{field: None})  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
