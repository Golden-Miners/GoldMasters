"""Agent 3 donchian-breakout: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.strategies.agent_03 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent03Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_03.rules import prior_channel
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

# FIXTURE channel: 5 base bars (upper 100.5 at bar 4, lower 99.5) + 2 breakouts.
FIXTURE_BASE = [
    ("100", "100.4", "99.6"),
    ("100.2", "100.3", "99.9"),
    ("99.8", "100.1", "99.5"),
    ("100.1", "100.2", "99.8"),
    ("100.3", "100.5", "100.0"),
]
FIXTURE_BREAK_LONG = [make_bar(close=c, high=h, low=l, index=i) for i, (c, h, l) in enumerate(
    [*FIXTURE_BASE, ("101", "102", "100.2"), ("101.5", "102.5", "100.9")]
)]
FIXTURE_SHORT_BASE = [
    ("100", "100.4", "99.6"),
    ("99.8", "100.1", "99.7"),
    ("100.2", "100.5", "99.9"),
    ("99.9", "100.0", "99.8"),
    ("99.7", "99.9", "99.5"),
]
FIXTURE_BREAK_SHORT = [
    make_bar(close=c, high=h, low=l, index=i)
    for i, (c, h, l) in enumerate([*FIXTURE_SHORT_BASE, ("99", "99.8", "98.5"), ("98.5", "99.1", "98.0")])
]


def _params(**overrides: object) -> Agent03Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 7,
        "channel_bars": 5,
        "buffer_ticks": 2,
        "confirm_bars": 2,
        "exit_bars": 5,
    }
    fields.update(overrides)
    return Agent03Params(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(FIXTURE_BREAK_LONG, make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "donchian-breakout"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)


def test_all_pass_short_yields_stamped_setup() -> None:
    evaluation = evaluate(
        FIXTURE_BREAK_SHORT,
        make_ctx(regime=TrendRegime.DOWNTREND),
        _params(),
    )
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None


def _long_variant(last_two: list[tuple[str, str, str]]) -> list:
    return [
        make_bar(close=c, high=h, low=l, index=i)
        for i, (c, h, l) in enumerate([*FIXTURE_BASE, *last_two])
    ]


def test_each_rule_fail_yields_no_setup() -> None:
    flat = bars_from_closes(["100"] * 7)
    cases = [
        ("break", flat, TrendRegime.UPTREND, {}),
        ("confirmation", _long_variant([("100.2", "100.4", "99.9"), ("101.5", "102.5", "100.9")]), TrendRegime.UPTREND, {}),
        ("buffer", _long_variant([("100.51", "100.7", "100.3"), ("100.51", "100.7", "100.3")]), TrendRegime.UPTREND, {}),
        ("regime", FIXTURE_BREAK_LONG, TrendRegime.DOWNTREND, {}),
        ("freshness", FIXTURE_BREAK_LONG, TrendRegime.UPTREND, {"exit_bars": 1}),
    ]
    for label, bars, regime, override in cases:
        evaluation = evaluate(bars, make_ctx(regime=regime), _params(**override))
        assert evaluation.setup_found is False, label
        assert evaluation.candidate_levels is None, label


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102", "104", "106"])
    evaluation = evaluate(short, make_ctx(), _params(min_bars=4))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(FIXTURE_BREAK_LONG, make_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="channel-break", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


def test_insufficient_data_branches() -> None:
    short = evaluate(FIXTURE_BREAK_LONG[:3], make_ctx(), _params())
    assert short.setup_found is False
    assert short.limitations == ["INSUFFICIENT_DATA"]
    no_tick = evaluate(FIXTURE_BREAK_LONG, make_ctx(tick_size=None), _params())
    assert no_tick.setup_found is False
    assert no_tick.limitations == ["INSUFFICIENT_DATA"]
    from goldmasters_contracts import TrendRegime as TR

    unknown_regime = evaluate(FIXTURE_BREAK_LONG, make_ctx(regime=TR.UNKNOWN), _params())
    assert unknown_regime.setup_found is False
    assert unknown_regime.limitations == ["INSUFFICIENT_DATA"]


def test_not_applicable_scope_branch() -> None:
    out = evaluate(FIXTURE_BREAK_LONG, make_ctx(instrument_id="eurusd"), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(instrument_id="eurusd"))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], make_ctx())[STRATEGY_ID] == "eligible"


def test_no_look_ahead() -> None:
    params = _params()
    before = prior_channel(FIXTURE_BREAK_LONG, params)
    assert before is not None
    assert before.upper == Decimal("100.5")
    extended = [*FIXTURE_BREAK_LONG, make_bar(close="103", index=7)]
    assert prior_channel(extended[:7], params) == before
    assert evaluate(FIXTURE_BREAK_LONG, make_ctx(), params) == evaluate(
        list(FIXTURE_BREAK_LONG), make_ctx(), params
    )


def test_determinism() -> None:
    assert evaluate(FIXTURE_BREAK_LONG, make_ctx(), _params()) == evaluate(
        FIXTURE_BREAK_LONG, make_ctx(), _params()
    )


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_03"))


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = list(FIXTURE_BREAK_LONG)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize("field", ["channel_bars", "buffer_ticks", "confirm_bars", "exit_bars"])
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(FIXTURE_BREAK_LONG, make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
