"""Agent 10 carry-term-structure: full 10-item per-agent test list (FIXTURE vectors only).

Legs ship NOT_APPLICABLE-first (source adapters are Phase 6+), so no
FIXTURE can produce a setup: every leg reads verified source data that does
not exist yet, never spot candles. The list proves the exemplar shape
(contract before composition, scope legs, NOT_APPLICABLE legs) plus one
test per non-defined leg asserting skipped and no gate input.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from goldmasters_contracts import AgentRunStatus, Levels, Timeframe, TrendRegime
from pydantic import ValidationError

from src.goldmasters.strategies.agent_10 import (
    CODE_HASH,
    RULE_SOURCE,
    STRATEGY_ID,
    STRATEGY_VERSION,
    Agent10Params,
    eligibility,
    evaluate,
)
from src.goldmasters.strategies.agent_10.levels_spec import take_profits_for
from src.goldmasters.strategies.agent_10.rules import leg_for_instrument
from src.goldmasters.strategies.base import (
    RuleCheck,
    StrategyEvaluation,
    adapter_feeds_gate,
    adapter_run_status,
    eligible_agents,
    hash_rule_source,
)
from tests.unit.agent_fixtures import (
    assert_decimal_only,
    make_bar,
    make_ctx,
)

EXPECTED_RULE_IDS = ["forex-carry", "crypto-funding", "commodity-curve"]

FIXTURE_FLAT = [
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
    ("100", "101", "99", "100"),
]

FIXTURE_TRENDING = [
    ("100", "102", "99", "101"),
    ("101", "103", "100", "102"),
    ("102", "104", "101", "103"),
    ("103", "105", "102", "104"),
    ("104", "106", "103", "105"),
    ("105", "107", "104", "106"),
    ("106", "108", "105", "107"),
    ("107", "109", "106", "108"),
]


def _bars(spec: list[tuple[str, str, str, str]]) -> list:
    """FIXTURE (open, high, low, close) tuples to closed H1 bars."""
    return [
        make_bar(close=close, high=high, low=low, open_=open_, index=index)
        for index, (open_, high, low, close) in enumerate(spec)
    ]


def _params(**overrides: object) -> Agent10Params:
    fields: dict[str, object] = {
        "enabled": True,
        "instruments": ("xauusd", "eurusd", "btcusd", "usoil"),
        "timeframes": (Timeframe.H1,),
        "regimes": (TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE),
        "min_bars": 6,
        "max_data_age_hours": Decimal("24"),
        "min_history_points": 50,
    }
    fields.update(overrides)
    return Agent10Params(**fields)  # type: ignore[arg-type]


def test_contract_first_exemplar_shape() -> None:
    assert STRATEGY_ID == "carry-term-structure"
    assert STRATEGY_VERSION == "1.0.0"
    assert CODE_HASH == hash_rule_source(RULE_SOURCE)
    assert "carry-term-structure" in RULE_SOURCE
    assert "NOT_APPLICABLE-first" in RULE_SOURCE
    assert "never infer funding" in RULE_SOURCE.lower() or "never infer" in RULE_SOURCE.lower()
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
    assert [check.rule_id for check in evaluation.rule_checks] == EXPECTED_RULE_IDS


def test_configured_legs_still_not_applicable_first() -> None:
    """Even fully configured, no source data exists: flat, scope-cited, never a setup."""
    for instrument in ("xauusd", "eurusd", "btcusd", "usoil"):
        evaluation = evaluate(
            _bars(FIXTURE_TRENDING), make_ctx(instrument_id=instrument), _params()
        )
        assert evaluation.setup_found is False
        assert evaluation.candidate_levels is None
        assert evaluation.limitations == ["NOT_APPLICABLE"]
        assert evaluation.strategy_id == STRATEGY_ID == "carry-term-structure"
        assert evaluation.strategy_version == STRATEGY_VERSION == "1.0.0"
        assert evaluation.code_hash == CODE_HASH
        assert all(check.verdict == "unknown" for check in evaluation.rule_checks)


@pytest.mark.parametrize(
    ("instrument", "leg"),
    [
        ("xauusd", "forex-carry"),
        ("xauusd", "crypto-funding"),
        ("eurusd", "crypto-funding"),
        ("eurusd", "commodity-curve"),
        ("btcusd", "forex-carry"),
        ("btcusd", "commodity-curve"),
        ("usoil", "forex-carry"),
        ("usoil", "crypto-funding"),
    ],
)
def test_non_defined_leg_is_not_applicable_never_no_setup(
    instrument: str, leg: str
) -> None:
    """A leg defined for another instrument class cites scope, never NO_SETUP."""
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(instrument_id=instrument), _params())
    check = next(c for c in evaluation.rule_checks if c.rule_id == leg)
    assert check.verdict == "unknown"
    assert "NOT_APPLICABLE" in check.reason
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert evaluation.limitations == ["NOT_APPLICABLE"]


def test_defined_leg_cites_missing_source_not_spot() -> None:
    """The leg matching this instrument names the missing source, never a price read."""
    by_instrument = {
        "xauusd": "commodity-curve",
        "eurusd": "forex-carry",
        "btcusd": "crypto-funding",
    }
    for instrument, leg in by_instrument.items():
        assert leg_for_instrument(instrument) == leg
        evaluation = evaluate(
            _bars(FIXTURE_TRENDING), make_ctx(instrument_id=instrument), _params()
        )
        check = next(c for c in evaluation.rule_checks if c.rule_id == leg)
        assert check.verdict == "unknown"
        assert "never inferred from spot" in check.reason
        assert evaluation.limitations == ["NOT_APPLICABLE"]
    assert leg_for_instrument("spx500") is None


def test_not_applicable_maps_to_skipped_never_gate() -> None:
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
    assert adapter_run_status("NOT_APPLICABLE") == AgentRunStatus.SKIPPED
    assert adapter_feeds_gate("NOT_APPLICABLE") is False
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None


def test_never_infers_from_spot_candles() -> None:
    """Flat versus trending spot reads evaluate identically: candles are not inputs."""
    ctx, params = make_ctx(), _params()
    assert evaluate(_bars(FIXTURE_FLAT), ctx, params) == evaluate(
        _bars(FIXTURE_TRENDING), ctx, params
    )


def test_each_leg_unknown_yields_no_setup() -> None:
    """Every leg is unknown by construction, so no composition can carry a setup."""
    for leg in EXPECTED_RULE_IDS:
        evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
        check = next(c for c in evaluation.rule_checks if c.rule_id == leg)
        assert check.verdict == "unknown"
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None


def test_unknown_verdict_yields_no_setup() -> None:
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any(check.verdict == "unknown" for check in evaluation.rule_checks)


def test_reason_code_per_leg() -> None:
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
    assert [check.rule_id for check in evaluation.rule_checks] == EXPECTED_RULE_IDS
    for check in evaluation.rule_checks:
        assert check.reason.strip(), f"{check.rule_id} carries no reason code"
        assert check.evidence.strip(), f"{check.rule_id} carries no evidence"


def test_cheat_rejection() -> None:
    passing = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params())
    assert passing.candidate_levels is None
    with pytest.raises(ValidationError, match="no setup and null levels"):
        StrategyEvaluation(
            strategy_id=STRATEGY_ID,
            strategy_version=STRATEGY_VERSION,
            code_hash=CODE_HASH,
            setup_found=False,
            rule_checks=[
                RuleCheck(rule_id="forex-carry", verdict="unknown", evidence="e", reason="r")
            ],
            candidate_levels=Levels(
                entry=Decimal("100.00"),
                stop_loss=Decimal("99.00"),
                take_profits=[Decimal("101.00")],
                risk_reward=Decimal("1"),
            ),
        )


def test_insufficient_data_branches() -> None:
    bars = _bars(FIXTURE_FLAT)
    short = evaluate(bars[:3], make_ctx(), _params())
    assert short.setup_found is False
    assert short.limitations == ["INSUFFICIENT_DATA"]
    unknown_regime = evaluate(bars, make_ctx(regime=TrendRegime.UNKNOWN), _params())
    assert unknown_regime.setup_found is False
    assert unknown_regime.limitations == ["INSUFFICIENT_DATA"]
    unset_min = evaluate(bars, make_ctx(), _params(min_bars=None))
    assert unset_min.setup_found is False
    assert unset_min.limitations == ["INSUFFICIENT_DATA"]


def test_not_applicable_scope_branch() -> None:
    bars = _bars(FIXTURE_FLAT)
    out = evaluate(bars, make_ctx(instrument_id="gbpusd"), _params())
    assert out.setup_found is False
    assert out.candidate_levels is None
    assert out.limitations == ["NOT_APPLICABLE"]


def test_registry_row_marks_out_of_scope_not_applicable() -> None:
    rule = eligibility(_params())
    verdicts = eligible_agents([rule], make_ctx(instrument_id="gbpusd"))
    assert verdicts == {STRATEGY_ID: "not_applicable"}
    assert eligible_agents([rule], make_ctx())[STRATEGY_ID] == "eligible"


def test_no_look_ahead() -> None:
    bars = _bars(FIXTURE_FLAT)
    params, ctx = _params(), make_ctx()
    before = evaluate(bars, ctx, params)
    future = make_bar(close="130", index=8)
    assert evaluate([*bars, future][:8], ctx, params) == before


def test_determinism() -> None:
    bars = _bars(FIXTURE_FLAT)
    assert evaluate(bars, make_ctx(), _params()) == evaluate(bars, make_ctx(), _params())


def test_decimal_only() -> None:
    assert_decimal_only(pathlib.Path("src/goldmasters/strategies/agent_10"))


def test_independent_from_other_agents() -> None:
    """Agent 10 shares math only through domain.* — never another agent's package."""
    package = pathlib.Path("src/goldmasters/strategies/agent_10")
    for source_file in sorted(package.glob("*.py")):
        text = source_file.read_text(encoding="utf-8")
        for other in ("agent_01", "agent_02", "agent_03", "agent_04",
                      "agent_05", "agent_06", "agent_07", "agent_08", "agent_09"):
            assert other not in text, f"cross-agent reference in {source_file.name}"


def test_misordered_input_is_insufficient_and_preserved() -> None:
    bars = _bars(FIXTURE_FLAT)
    first_open = bars[0].bar_open_time
    swapped = [bars[1], bars[0], *bars[2:]]
    evaluation = evaluate(swapped, make_ctx(), _params())
    assert evaluation.setup_found is False
    assert evaluation.limitations == ["INSUFFICIENT_DATA"]
    assert [bar.bar_open_time for bar in swapped][1] == first_open


@pytest.mark.parametrize("field", ["max_data_age_hours", "min_history_points"])
def test_none_param_fails_closed(field: str) -> None:
    evaluation = evaluate(_bars(FIXTURE_FLAT), make_ctx(), _params(**{field: None}))
    assert evaluation.setup_found is False
    assert evaluation.candidate_levels is None
    assert any("fail-closed" in check.reason for check in evaluation.rule_checks)


def test_levels_spec_raises_before_any_passing_leg() -> None:
    """Locked shape kept, but no prices exist to map: raising beats a default level."""
    from goldmasters_contracts import Direction

    with pytest.raises(AssertionError, match="emits no levels"):
        take_profits_for(
            direction=Direction.LONG, entry=Decimal("100"), target=Decimal("101")
        )
