"""Agent 1 trend-following: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.domain.indicators import ema_close
from src.goldmasters.strategies.agent_01 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent01Params,
    eligibility,
    evaluate,
)
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

FIXTURE_UP = ["100", "102", "104", "106", "108", "110", "112", "114"]
FIXTURE_DOWN = ["114", "112", "110", "108", "106", "104", "102", "100"]
FIXTURE_FLAT = ["100"] * 8


def _params(**overrides: object) -> Agent01Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 6,
        "fast_period": 3,
        "slow_period": 5,
        "htf_timeframe": "H4",
        "adx_min": Decimal("0.1"),
        "confirm_bars": 2,
    }
    fields.update(overrides)
    return Agent01Params(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "trend-following"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)


def test_all_pass_short_yields_stamped_setup() -> None:
    evaluation = evaluate(
        bars_from_closes(FIXTURE_DOWN),
        make_ctx(regime=TrendRegime.DOWNTREND),
        _params(),
    )
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None


@pytest.mark.parametrize(
    ("label", "closes", "ctx_regime"),
    [
        ("trend", FIXTURE_FLAT, TrendRegime.UPTREND),
        (
            "strength",
            ["100", "100.05", "100.10", "100.15", "100.20", "100.25", "100.30", "100.35"],
            TrendRegime.UPTREND,
        ),
        (
            "confirmation",
            ["100", "102", "104", "106", "108", "110", "112", "106"],
            TrendRegime.UPTREND,
        ),
        ("htf", FIXTURE_UP, TrendRegime.DOWNTREND),
    ],
)
def test_each_rule_fail_yields_no_setup(label: str, closes: list[str], ctx_regime: object) -> None:
    evaluation = evaluate(
        bars_from_closes(closes), make_ctx(regime=ctx_regime), _params()  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102", "104", "106"])
    evaluation = evaluate(short, make_ctx(), _params(min_bars=4))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="trend-alignment", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


@pytest.mark.parametrize("regime", [TrendRegime.UPTREND, TrendRegime.DOWNTREND])
def test_insufficient_data_branches(regime: TrendRegime) -> None:
    bars = bars_from_closes(FIXTURE_UP)
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
    bars = bars_from_closes(FIXTURE_UP)
    out = evaluate(bars, make_ctx(instrument_id="eurusd"), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(instrument_id="eurusd"))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], make_ctx())[STRATEGY_ID] == "eligible"


def test_no_look_ahead() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    params = _params()
    ctx = make_ctx()
    prefix = bars[:6]
    before = evaluate(prefix, ctx, params)
    future = make_bar(close="130", index=6)
    assert evaluate(prefix, ctx, params) == before
    assert ema_close(prefix, period=3) == ema_close([*prefix, future][:6], period=3)


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    assert evaluate(bars, make_ctx(), _params()) == evaluate(bars, make_ctx(), _params())


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_01"))


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize(
    "field",
    ["fast_period", "slow_period", "htf_timeframe", "adx_min", "confirm_bars"],
)
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
