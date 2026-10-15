"""Agent 7 mean-reversion: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.domain.indicators import sma_close
from src.goldmasters.strategies.agent_07 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent07Params,
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

# Single-spike extensions: z ≈ ∓1.15 clears z_min 1.0 and the 1-sigma band.
FIXTURE_LONG = ["100", "100", "100", "100", "100", "85", "86"]
FIXTURE_SHORT = ["100", "100", "100", "100", "100", "115", "114"]
FIXTURE_FLAT = ["100"] * 7
# Spike then flat: band and RSI pass, but the last step never turns (move 0).
FIXTURE_NO_TURN = ["100", "100", "100", "100", "100", "115", "115"]
# Whipsaw ending extended: band passes short, RSI stays mid (also no turn).
FIXTURE_WHIPSAW = ["100", "110", "100", "110", "100", "110", "112"]


def _params(**overrides: object) -> Agent07Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE),
        "min_bars": 6,
        "basis_period": 5,
        "band_width": Decimal("1.0"),
        "z_min": Decimal("1.0"),
        "rsi_period": 5,
        "rsi_extreme": Decimal("30"),
        "confirm_bars": 1,
    }
    fields.update(overrides)
    return Agent07Params(**fields)  # type: ignore[arg-type]


def _range_ctx(**overrides: object) -> object:
    fields: dict[str, object] = {"regime": TrendRegime.RANGE}
    fields.update(overrides)
    return make_ctx(**fields)  # type: ignore[arg-type]


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_LONG), _range_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "mean-reversion"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)


def test_all_pass_short_yields_stamped_setup() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_SHORT), _range_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None


@pytest.mark.parametrize(
    ("label", "closes", "ctx_regime"),
    [
        ("gate", FIXTURE_LONG, TrendRegime.UPTREND),
        ("band", FIXTURE_FLAT, TrendRegime.RANGE),
        ("rsi", FIXTURE_WHIPSAW, TrendRegime.RANGE),
        ("confirmation", FIXTURE_NO_TURN, TrendRegime.RANGE),
    ],
)
def test_each_rule_fail_yields_no_setup(label: str, closes: list[str], ctx_regime: object) -> None:
    del label
    evaluation = evaluate(
        bars_from_closes(closes), make_ctx(regime=ctx_regime), _params()  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102", "104", "106"])
    evaluation = evaluate(short, _range_ctx(), _params(min_bars=4))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_cheat_rejection() -> None:
    passing = evaluate(bars_from_closes(FIXTURE_LONG), _range_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="band-extension", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


@pytest.mark.parametrize("regime", [TrendRegime.RANGE])
def test_insufficient_data_branches(regime: TrendRegime) -> None:
    bars = bars_from_closes(FIXTURE_LONG)
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
    bars = bars_from_closes(FIXTURE_LONG)
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
    bars = bars_from_closes(FIXTURE_LONG)
    params = _params()
    ctx = _range_ctx()
    prefix = bars[:6]
    before = evaluate(prefix, ctx, params)  # type: ignore[arg-type]
    future = make_bar(close="130", index=6)
    assert evaluate(prefix, ctx, params) == before  # type: ignore[arg-type]
    assert sma_close(prefix, period=5) == sma_close([*prefix, future][:6], period=5)


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_LONG)
    assert evaluate(bars, _range_ctx(), _params()) == evaluate(  # type: ignore[arg-type]
        bars, _range_ctx(), _params()
    )


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_07"))


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = bars_from_closes(FIXTURE_LONG)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, _range_ctx(), _params())  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize(
    "field",
    ["basis_period", "band_width", "z_min", "rsi_period", "rsi_extreme", "confirm_bars"],
)
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(
        bars_from_closes(FIXTURE_LONG), _range_ctx(), _params(**{field: None})  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
