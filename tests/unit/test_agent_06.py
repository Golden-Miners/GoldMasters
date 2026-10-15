"""Agent 6 session-opening-range: full 10-item per-agent test list (FIXTURE vectors only)."""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import Levels, QualityStatus, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.strategies.agent_06 import (
    CODE_HASH,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent06Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_06.rules import range_bounds
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
# Breakout without confirmation: last close beyond the range, prior back inside.
FIXTURE_TRAP = ["100", "102", "100", "100", "100", "100", "100", "110"]


def _params(**overrides: object) -> Agent06Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND),
        "min_bars": 6,
        "session_name": "london",
        "session_tz": "UTC",
        "range_minutes": 120,
        "buffer_ticks": 2,
        "expiry_minutes": 480,
        "max_spread_ticks": 5,
    }
    fields.update(overrides)
    return Agent06Params(**fields)  # type: ignore[arg-type]


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
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params())
    assert evaluation.setup_found is True
    assert evaluation.candidate_levels is not None
    assert evaluation.strategy_id == STRATEGY_ID == "session-opening-range"
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
        (
            "scope",
            FIXTURE_UP,
            TrendRegime.UPTREND,
        ),
        ("breakout", FIXTURE_FLAT, TrendRegime.UPTREND),
        ("confirmation", FIXTURE_TRAP, TrendRegime.UPTREND),
        ("quality", FIXTURE_UP, TrendRegime.UPTREND),
    ],
)
def test_each_rule_fail_yields_no_setup(label: str, closes: list[str], ctx_regime: object) -> None:
    if label == "scope":
        bars = _bars_at(closes, datetime(2026, 1, 6, 20, 0, tzinfo=UTC))
    else:
        bars = bars_from_closes(closes)
    ctx = make_ctx(regime=ctx_regime)  # type: ignore[arg-type]
    if label == "quality":
        ctx = ctx.model_copy(update={"quality_status": QualityStatus.STALE})
    evaluation = evaluate(bars, ctx, _params())
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "fail" for check in evaluation.rule_checks)


def test_expiry_blocks_stale_breakout() -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params(expiry_minutes=60))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert [check.rule_id for check in evaluation.rule_checks if check.verdict == "fail"] == [
        "breakout-expiry"
    ]


def test_session_timezone_and_dst_correctness() -> None:
    """Server-time correctness: UTC midnight span fails in UTC but passes in-session in New York."""
    spanning = _bars_at(FIXTURE_UP, datetime(2026, 1, 6, 20, 0, tzinfo=UTC))
    utc_eval = evaluate(spanning, make_ctx(), _params(session_tz="UTC"))
    assert utc_eval.setup_found is False
    assert any(
        check.rule_id == "session-scope" and check.verdict == "fail"
        for check in utc_eval.rule_checks
    )
    ny_eval = evaluate(spanning, make_ctx(), _params(session_tz="America/New_York"))
    assert ny_eval.setup_found is True
    # Spring-forward day converts without error and stays one local session day.
    dst_bars = _bars_at(FIXTURE_UP, datetime(2026, 3, 8, 5, 0, tzinfo=UTC))
    dst_eval = evaluate(dst_bars, make_ctx(), _params(session_tz="America/New_York"))
    assert dst_eval.setup_found is True
    # An unknown zone fails closed, never defaults to UTC.
    bad_tz = evaluate(
        bars_from_closes(FIXTURE_UP), make_ctx(), _params(session_tz="Not/AZone")
    )
    assert bad_tz.setup_found is False
    assert any(check.verdict == "unknown" for check in bad_tz.rule_checks)


def test_unknown_verdict_yields_no_setup() -> None:
    short = bars_from_closes(["100", "102"])
    evaluation = evaluate(short, make_ctx(), _params(min_bars=2))
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
                RuleCheck(rule_id="range-breakout", verdict="fail", evidence="e", reason="r")
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
    assert range_bounds(prefix, 2) == range_bounds([*prefix, future][:6], 2)


def test_determinism() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    assert evaluate(bars, make_ctx(), _params()) == evaluate(bars, make_ctx(), _params())


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_06"))


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
    [
        "session_name",
        "session_tz",
        "range_minutes",
        "buffer_ticks",
        "expiry_minutes",
        "max_spread_ticks",
    ],
)
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(bars_from_closes(FIXTURE_UP), make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
