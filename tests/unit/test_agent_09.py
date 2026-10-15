"""Agent 9 smc-ict-liquidity-sweep: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.strategies.agent_09 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent09Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_09.rules import rule_liquidity_pool
from src.goldmasters.strategies.base import (
    Direction,
    RuleCheck,
    StrategyEvaluation,
    eligible_agents,
)
from tests.unit.agent_fixtures import (
    assert_decimal_only,
    make_bar,
    make_ctx,
)

# FIXTURE bearish sweep: equal swing highs at 110 (bars 1, 3), sweep bar 5
# pokes one tick beyond and rejects, bar 6 displaces through the swing low
# at 98, bar 7 retests the OB (100-109) and confirms down, entry 102,
# stop beyond the sweep 110.01, target opposing pool 98.
FIXTURE_SHORT = [
    ("100", "101", "99", "100"),
    ("101", "110", "99.5", "105"),
    ("105", "106", "98", "104"),
    ("104", "110", "99", "107"),
    ("107", "109", "100", "108"),
    ("108", "110.01", "107", "107.5"),
    ("107.5", "108", "96", "96.5"),
    ("104", "105", "101", "102"),
]

# Mirrors of the cases below that only flip closes/opens inside fixed ranges.
FIXTURE_ALL_BEARISH_PREFIX = [
    ("100.5", "101", "99", "100"),
    ("106", "110", "99.5", "105"),
    ("104.5", "106", "98", "104"),
    ("107.5", "110", "99", "107"),
    ("108.5", "109", "100", "108"),
    ("108", "110.01", "107", "107.5"),
    ("107.5", "108", "96", "96.5"),
    ("104", "105", "101", "102"),
]

FIXTURE_RISING_LOWS_PREFIX = [
    ("100", "101", "100", "100"),
    ("101", "110", "100.5", "105"),
    ("105", "106", "101", "104"),
    ("104", "110", "101.5", "107"),
    ("107", "109", "102", "108"),
    ("108", "110.01", "107", "107.5"),
    ("107.5", "108", "96", "96.5"),
    ("104", "105", "101", "102"),
]

EXPECTED_RULE_IDS = [
    "htf-bias",
    "liquidity-pool",
    "liquidity-sweep",
    "displacement",
    "structure-shift",
    "order-block-zone",
    "retest-confirm",
    "trade-plan",
]


def _bars(spec: list[tuple[str, str, str, str]]) -> list:
    """FIXTURE (open, high, low, close) tuples to closed H1 bars."""
    return [
        make_bar(close=close, high=high, low=low, open_=open_, index=index)
        for index, (open_, high, low, close) in enumerate(spec)
    ]


def _mirror(bars: list) -> list:
    """Bearish FIXTURE to its bullish image: prices negated about 210.

    Highs and lows swap so ranges stay valid; direction flips while every
    spread — and therefore every tick-tolerance read — is preserved.
    """
    pivot = Decimal(210)
    return [
        bar.model_copy(
            update={
                "open": pivot - bar.open,
                "high": pivot - bar.low,
                "low": pivot - bar.high,
                "close": pivot - bar.close,
            }
        )
        for bar in bars
    ]


def _params(**overrides: object) -> Agent09Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE),
        "min_bars": 6,
        "swing_bars": 1,
        "equal_tol_ticks": 2,
        "sweep_tol_ticks": 2,
        "disp_body_min_atr": Decimal("1.0"),
        "expiry_bars": 5,
    }
    fields.update(overrides)
    return Agent09Params(**fields)  # type: ignore[arg-type]


def _down_ctx(**overrides: object) -> object:
    fields: dict[str, object] = {"regime": TrendRegime.DOWNTREND}
    fields.update(overrides)
    return make_ctx(**fields)  # type: ignore[arg-type]


def _up_ctx(**overrides: object) -> object:
    fields: dict[str, object] = {"regime": TrendRegime.UPTREND}
    fields.update(overrides)
    return make_ctx(**fields)  # type: ignore[arg-type]


def _mutate(bars: list, index: int, **updates: object) -> list:
    mutated = list(bars)
    mutated[index] = mutated[index].model_copy(update=updates)
    return mutated


def test_all_pass_short_yields_stamped_setup() -> None:
    evaluation = evaluate(_bars(FIXTURE_SHORT), _down_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "smc-ict-liquidity-sweep"
    assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
    assert evaluation.code_hash == CODE_HASH
    assert [check.rule_id for check in evaluation.rule_checks] == EXPECTED_RULE_IDS
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)
    levels = evaluation.candidate_levels
    assert levels.stop_loss > levels.entry > levels.take_profits[0]
    sweep = next(c for c in evaluation.rule_checks if c.rule_id == "liquidity-sweep")
    assert "within" in sweep.evidence


def test_all_pass_long_yields_stamped_setup() -> None:
    evaluation = evaluate(_mirror(_bars(FIXTURE_SHORT)), _up_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert all(check.verdict == "pass" for check in evaluation.rule_checks)
    levels = evaluation.candidate_levels
    assert levels.take_profits[0] > levels.entry > levels.stop_loss


def _failing_case(label: str) -> tuple:
    """One broken step per label; every other step keeps its FIXTURE read."""
    bars = _bars(FIXTURE_SHORT)
    ctx: object = _down_ctx()
    params_kwargs: dict[str, object] = {}
    if label == "htf-bias":
        ctx = make_ctx(regime=TrendRegime.RANGE)
    elif label == "liquidity-pool":
        bars = _mutate(bars, 3, high=Decimal("115"))
    elif label == "liquidity-sweep":
        bars = _mutate(bars, 5, high=Decimal("112"))
    elif label == "displacement":
        bars = _mutate(
            bars,
            6,
            open=Decimal("107.5"),
            high=Decimal("108"),
            low=Decimal("106"),
            close=Decimal("107"),
        )
    elif label == "structure-shift":
        bars = _bars(FIXTURE_RISING_LOWS_PREFIX)
    elif label == "order-block-zone":
        bars = _bars(FIXTURE_ALL_BEARISH_PREFIX)
    elif label == "retest-confirm":
        bars = _mutate(
            bars,
            7,
            open=Decimal("99"),
            high=Decimal("99.5"),
            low=Decimal("97"),
            close=Decimal("98"),
        )
    elif label == "trade-plan":
        params_kwargs = {"expiry_bars": 3}
    else:  # pragma: no cover - parametrize lists every step
        raise AssertionError(f"unknown step {label}")
    return bars, ctx, params_kwargs


@pytest.mark.parametrize("label", EXPECTED_RULE_IDS)
def test_each_rule_fail_yields_no_setup(label: str) -> None:
    bars, ctx, params_kwargs = _failing_case(label)
    evaluation = evaluate(bars, ctx, _params(**params_kwargs))  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "fail" for check in evaluation.rule_checks)


def test_unknown_verdict_yields_no_setup() -> None:
    evaluation = evaluate(
        _bars(FIXTURE_SHORT), _down_ctx(), _params(swing_bars=None)  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_lone_zone_never_signals() -> None:
    """A proven zone without confirmation — and a full read without a plan — stay flat."""
    bars, ctx, params_kwargs = _failing_case("retest-confirm")
    evaluation = evaluate(bars, ctx, _params(**params_kwargs))  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    by_id = {check.rule_id: check for check in evaluation.rule_checks}
    assert by_id["order-block-zone"].verdict == "pass"
    assert by_id["retest-confirm"].verdict == "fail"
    planned, _, _ = _failing_case("trade-plan")
    stale = evaluate(planned, ctx, _params(expiry_bars=3))
    assert stale.setup_found is False
    assert stale.rule_checks[-1].verdict == "fail"


def test_reason_code_per_step() -> None:
    evaluation = evaluate(_bars(FIXTURE_SHORT), _down_ctx(), _params())
    assert [check.rule_id for check in evaluation.rule_checks] == EXPECTED_RULE_IDS
    for check in evaluation.rule_checks:
        assert check.reason.strip(), f"{check.rule_id} carries no reason code"
        assert check.evidence.strip(), f"{check.rule_id} carries no evidence"
    failing = evaluate(*_failing_case("liquidity-sweep")[:2], _params())  # type: ignore[arg-type]
    failed = [c for c in failing.rule_checks if c.verdict == "fail"]
    assert failed and all(c.reason.strip() for c in failed)


def test_cheat_rejection() -> None:
    passing = evaluate(_bars(FIXTURE_SHORT), _down_ctx(), _params())
    assert passing.candidate_levels is not None
    levels: Levels = passing.candidate_levels
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=True,
            rule_checks=[
                RuleCheck(rule_id="liquidity-sweep", verdict="fail", evidence="e", reason="r")
            ],
            candidate_levels=levels,
        )


@pytest.mark.parametrize("regime", [TrendRegime.DOWNTREND])
def test_insufficient_data_branches(regime: TrendRegime) -> None:
    bars = _bars(FIXTURE_SHORT)
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
    bars = _bars(FIXTURE_SHORT)
    out = evaluate(bars, make_ctx(instrument_id="eurusd", regime=TrendRegime.DOWNTREND), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(instrument_id="eurusd"))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], _down_ctx())[STRATEGY_ID] == "eligible"  # type: ignore[arg-type]


def test_no_look_ahead() -> None:
    bars = _bars(FIXTURE_SHORT)
    params = _params()
    ctx = _down_ctx()
    prefix = bars[:7]
    before = evaluate(prefix, ctx, params)  # type: ignore[arg-type]
    future = make_bar(close="130", index=7)
    assert evaluate(prefix, ctx, params) == before  # type: ignore[arg-type]
    tick = Decimal("0.01")
    assert rule_liquidity_pool(prefix, tick, params, Direction.SHORT)[1:] == (
        rule_liquidity_pool([*prefix, future][:7], tick, params, Direction.SHORT)[1:]
    )


def test_determinism() -> None:
    bars = _bars(FIXTURE_SHORT)
    assert evaluate(bars, _down_ctx(), _params()) == evaluate(  # type: ignore[arg-type]
        bars, _down_ctx(), _params()
    )


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_09"))


def test_independent_from_other_agents() -> None:
    """Agent 9 shares math only through domain.* — never another agent's package."""
    package = pathlib.Path("src/goldmasters/strategies/agent_09")
    for source_file in sorted(package.glob("*.py")):
        text = source_file.read_text(encoding="utf-8")
        for other in ("agent_01", "agent_02", "agent_03", "agent_04",
                      "agent_05", "agent_06", "agent_07", "agent_08"):
            assert other not in text, f"cross-agent reference in {source_file.name}"


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = _bars(FIXTURE_SHORT)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, _down_ctx(), _params())  # type: ignore[arg-type]
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize(
    "field",
    ["swing_bars", "equal_tol_ticks", "sweep_tol_ticks", "disp_body_min_atr", "expiry_bars"],
)
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(
        _bars(FIXTURE_SHORT), _down_ctx(), _params(**{field: None})  # type: ignore[arg-type]
    )
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
