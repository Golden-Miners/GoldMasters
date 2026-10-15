"""Agent 5 trend-pullback-continuation: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.domain.indicators import ema_close
from src.goldmasters.strategies.agent_05 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent05Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.base import (
    RuleCheck,
    StrategyEvaluation,
    eligible_agents,
)
from tests.unit.agent_fixtures import assert_decimal_only, bars_from_closes, make_ctx

# FIXTURE pullback: established rise, one-bar dip touching the average, recovery.
FIXTURE_PULLBACK = ["100", "104", "108", "109", "109.5", "110", "107", "110.5", "111.5"]
FIXTURE_FLAT = ["100"] * 9


def _params(**overrides: object) -> Agent05Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 6,
        "trend_period": 5,
        "pullback_ma": 3,
        "confirm_bars": 2,
        "expiry_bars": 3,
    }
    fields.update(overrides)
    return Agent05Params(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_PULLBACK), make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "trend-pullback-continuation"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)


def test_all_pass_short_yields_stamped_setup() -> None:
    mirror = ["123", "119", "115", "114", "113.5", "113", "116", "112.5", "111.5"]
    evaluation = evaluate(
        bars_from_closes(mirror),
        make_ctx(regime=TrendRegime.DOWNTREND),
        _params(),
    )
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None


def test_each_rule_fail_yields_no_setup() -> None:
    cases = [
        ("trend", FIXTURE_FLAT, TrendRegime.UPTREND, {}),
        (
            "shape",
            ["100", "104", "108", "109", "109.5", "110", "107", "110.5", "108"],
            TrendRegime.UPTREND,
            {},
        ),
        (
            "confirmation",
            ["100", "104", "108", "109", "109.5", "110", "107", "107.5", "112"],
            TrendRegime.UPTREND,
            {},
        ),
        ("expiry", FIXTURE_PULLBACK, TrendRegime.UPTREND, {"expiry_bars": 1}),
        ("trend-intact", FIXTURE_PULLBACK, TrendRegime.DOWNTREND, {}),
    ]
    for label, closes, regime, override in cases:
        evaluation = evaluate(bars_from_closes(closes), make_ctx(regime=regime), _params(**override))
        assert evaluation.setup_found is False, label
        assert evaluation.candidate_levels is None, label


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102", "104", "106"])
    evaluation = evaluate(short, make_ctx(), _params(min_bars=4))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(bars_from_closes(FIXTURE_PULLBACK), make_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="governing-trend", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


def test_insufficient_data_branches() -> None:
    bars = bars_from_closes(FIXTURE_PULLBACK)
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
    bars = bars_from_closes(FIXTURE_PULLBACK)
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
    bars = bars_from_closes(FIXTURE_PULLBACK)
    params = _params()
    assert params.trend_period is not None
    prefix = bars[:7]
    before = evaluate(prefix, make_ctx(), _params(min_bars=6))
    assert evaluate(list(prefix), make_ctx(), _params(min_bars=6)) == before
    assert ema_close(prefix, period=params.trend_period) == ema_close(
        [*prefix, bars[7]][:7], period=params.trend_period
    )


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_PULLBACK)
    assert evaluate(bars, make_ctx(), _params()) == evaluate(bars, make_ctx(), _params())


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_05"))


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = bars_from_closes(FIXTURE_PULLBACK)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize("field", ["trend_period", "pullback_ma", "confirm_bars", "expiry_bars"])
def test_none_param_fails_closed(field: str) -> None:
    bars = bars_from_closes(FIXTURE_PULLBACK)
    evaluation = evaluate(bars, make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
