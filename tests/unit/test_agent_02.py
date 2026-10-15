"""Agent 2 time-series momentum: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.domain.indicators import average_true_range
from src.goldmasters.strategies.agent_02 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent02Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.base import (
    RuleCheck,
    StrategyEvaluation,
    eligible_agents,
)
from tests.unit.agent_fixtures import assert_decimal_only, bars_from_closes, make_ctx

FIXTURE_UP = ["100", "102", "104", "103", "105", "108"]
FIXTURE_DOWN = ["108", "106", "104", "105", "103", "100"]
FIXTURE_FLAT = ["100"] * 6


def _params(**overrides: object) -> Agent02Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 6,
        "lookbacks": (2, 4),
        "entry_threshold": Decimal("0.005"),
        "vol_lookback": 3,
        "max_hold_bars": 8,
        "expiry_bars": 3,
    }
    fields.update(overrides)
    return Agent02Params(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "time-series-momentum"
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


def test_each_rule_fail_yields_no_setup() -> None:
    cases = [
        ("momentum", FIXTURE_FLAT, TrendRegime.UPTREND, {}),
        ("vol", ["100"] * 6, TrendRegime.UPTREND, {}),
        ("horizon", FIXTURE_UP, TrendRegime.UPTREND, {"max_hold_bars": 2}),
        (
            "expiry",
            ["100", "102", "110", "108", "107", "109"],
            TrendRegime.UPTREND,
            {"expiry_bars": 2},
        ),
        ("regime", FIXTURE_UP, TrendRegime.DOWNTREND, {}),
    ]
    for label, closes, regime, override in cases:
        evaluation = evaluate(
            bars_from_closes(closes), make_ctx(regime=regime), _params(**override)
        )
        assert evaluation.setup_found is False, label
        assert evaluation.candidate_levels is None, label


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
                RuleCheck(rule_id="momentum-alignment", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


def test_insufficient_data_branches() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    short = evaluate(bars[:3], make_ctx(), _params())
    assert short.setup_found is False
    assert short.limitations == ["INSUFFICIENT_DATA"]
    no_tick = evaluate(bars, make_ctx(tick_size=None), _params())
    assert no_tick.setup_found is False
    assert no_tick.limitations == ["INSUFFICIENT_DATA"]
    from goldmasters_contracts import TrendRegime as TR

    unknown_regime = evaluate(bars, make_ctx(regime=TR.UNKNOWN), _params())
    assert unknown_regime.setup_found is False
    assert unknown_regime.limitations == ["INSUFFICIENT_DATA"]


def test_not_applicable_scope_branch() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    out = evaluate(bars, make_ctx(timeframe=Timeframe.M15), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(timeframe=Timeframe.M15))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], make_ctx())[STRATEGY_ID] == "eligible"


def test_no_look_ahead() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    params = _params()
    ctx = make_ctx()
    prefix = bars[:5]
    before = evaluate(prefix, ctx, _params(min_bars=4))
    assert evaluate(prefix, ctx, _params(min_bars=4)) == before
    assert average_true_range(prefix, period=2) == average_true_range(
        [*prefix, bars[5]][:5], period=2
    )
    assert params.lookbacks == (2, 4)


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    assert evaluate(bars, make_ctx(), _params()) == evaluate(bars, make_ctx(), _params())


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_02"))


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
    ["lookbacks", "entry_threshold", "vol_lookback", "max_hold_bars", "expiry_bars"],
)
def test_none_param_fails_closed(field: str) -> None:
    value: object = () if field == "lookbacks" else None
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params(**{field: value}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
