"""Agent 4 vol-expansion-breakout: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.domain.indicators import average_true_range
from src.goldmasters.strategies.agent_04 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent04Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_04.rules import trailing_atrs
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

# FIXTURE squeeze: volatile open, compressed middle, one-bar upside push.
FIXTURE_SQUEEZE = [
    make_bar(close=c, high=h, low=l, open_=o, index=i)
    for i, (o, c, h, l) in enumerate(
        [
            ("100", "104", "104.5", "99.5"),
            ("104", "100", "104.5", "99.5"),
            ("100", "104", "104.8", "99.8"),
            ("104", "103", "104.2", "102.7"),
            ("103", "104", "104.2", "103.0"),
            ("104", "103.5", "104.5", "103.5"),
            ("103.5", "104.3", "104.4", "103.5"),
            ("104.3", "105.5", "105.8", "104.3"),
        ]
    )
]
FIXTURE_RAMP = bars_from_closes(["100", "102", "104", "106", "108", "110", "112", "114"])


def _params(**overrides: object) -> Agent04Params:
    from decimal import Decimal

    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 7,
        "vol_lookback": 3,
        "compression_pctile": Decimal("0.5"),
        "confirm_bars": 2,
    }
    fields.update(overrides)
    return Agent04Params(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(FIXTURE_SQUEEZE, make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "vol-expansion-breakout"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)


def _flat_push_end() -> list:
    return [
        make_bar(close=c, high=h, low=l, open_=o, index=i)
        for i, (o, c, h, l) in enumerate(
            [
                ("100", "104", "104.5", "99.5"),
                ("104", "100", "104.5", "99.5"),
                ("100", "104", "104.8", "99.8"),
                ("104", "103", "104.2", "102.7"),
                ("103", "104", "104.2", "103.0"),
                ("104", "103.5", "104.5", "103.5"),
                ("103.5", "104.3", "104.4", "103.5"),
                ("104.3", "103.8", "104.4", "103.7"),
            ]
        )
    ]


def _gapped_push_end() -> list:
    tail = [
        make_bar(close=c, high=h, low=l, open_=o, index=i)
        for i, (o, c, h, l) in enumerate(
            [
                ("100", "104", "104.5", "99.5"),
                ("104", "100", "104.5", "99.5"),
                ("100", "104", "104.8", "99.8"),
                ("104", "103", "104.2", "102.7"),
                ("103", "104", "104.2", "103.0"),
                ("104", "103.5", "104.5", "103.5"),
                ("103.5", "104.3", "104.4", "103.5"),
                ("105.8", "105.5", "106.0", "104.5"),
            ]
        )
    ]
    return tail


def test_each_rule_fail_yields_no_setup() -> None:
    cases = [
        ("compression", FIXTURE_RAMP, TrendRegime.UPTREND),
        ("direction", _flat_push_end(), TrendRegime.UPTREND),
        ("reliability", _gapped_push_end(), TrendRegime.UPTREND),
        ("regime", FIXTURE_SQUEEZE, TrendRegime.DOWNTREND),
    ]
    for label, bars, regime in cases:
        evaluation = evaluate(bars, make_ctx(regime=regime), _params())
        assert evaluation.setup_found is False, label
        assert evaluation.candidate_levels is None, label


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102", "104", "106"])
    evaluation = evaluate(short, make_ctx(), _params(min_bars=4))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(FIXTURE_SQUEEZE, make_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="vol-compression", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


def test_insufficient_data_branches() -> None:
    short = evaluate(FIXTURE_SQUEEZE[:3], make_ctx(), _params())
    assert short.setup_found is False
    assert short.limitations == ["INSUFFICIENT_DATA"]
    no_tick = evaluate(FIXTURE_SQUEEZE, make_ctx(tick_size=None), _params())
    assert no_tick.setup_found is False
    assert no_tick.limitations == ["INSUFFICIENT_DATA"]
    from goldmasters_contracts import TrendRegime as TR

    unknown_regime = evaluate(FIXTURE_SQUEEZE, make_ctx(regime=TR.UNKNOWN), _params())
    assert unknown_regime.setup_found is False
    assert unknown_regime.limitations == ["INSUFFICIENT_DATA"]


def test_not_applicable_scope_branch() -> None:
    out = evaluate(FIXTURE_SQUEEZE, make_ctx(instrument_id="eurusd"), _params())
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
    assert params.vol_lookback is not None
    readings = trailing_atrs(FIXTURE_SQUEEZE, params.vol_lookback)
    assert readings is not None
    assert len(readings) == params.vol_lookback + 1
    extended = [*FIXTURE_SQUEEZE, make_bar(close="107", index=8)]
    assert trailing_atrs(extended[:8], params.vol_lookback) == readings
    assert average_true_range(FIXTURE_SQUEEZE[:5], period=3) == average_true_range(
        extended[:5], period=3
    )
    assert evaluate(FIXTURE_SQUEEZE, make_ctx(), params) == evaluate(
        list(FIXTURE_SQUEEZE), make_ctx(), params
    )


def test_determinism() -> None:
    assert evaluate(FIXTURE_SQUEEZE, make_ctx(), _params()) == evaluate(
        FIXTURE_SQUEEZE, make_ctx(), _params()
    )


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_04"))


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = list(FIXTURE_SQUEEZE)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize("field", ["vol_lookback", "compression_pctile", "confirm_bars"])
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(FIXTURE_SQUEEZE, make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
