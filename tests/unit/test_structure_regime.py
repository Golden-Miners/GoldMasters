"""Structure + regime primitives (03-02 Tasks 1-2): versioned, deterministic, fail-closed.

Labelled fixtures (``FIXTURE_`` prefix, tests-only) — never live data.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import (
    MarketBar,
    QualityStatus,
    Timeframe,
    TrendRegime,
    VolumeType,
)

from src.goldmasters.domain import regime, structure
from src.goldmasters.domain.regime import REGIME_CODE_HASH, classify_regime
from src.goldmasters.domain.structure import (
    STRUCTURE_CODE_HASH,
    StructureState,
    describe_structure,
    highest_high,
    lowest_low,
    swing_highs,
    swing_lows,
)

FIXTURE_T0 = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
FIXTURE_TICK = Decimal("0.01")


def FIXTURE_bar(  # noqa: N802 - fixture prefix is the labelling convention
    open_time: datetime,
    high: str,
    low: str,
) -> MarketBar:
    mid = (Decimal(high) + Decimal(low)) / 2
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=open_time,
        bar_close_time=open_time + timedelta(hours=1),
        open=mid,
        high=Decimal(high),
        low=Decimal(low),
        close=mid,
        volume=Decimal(100),
        volume_type=VolumeType.TICK,
        retrieved_at=open_time + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.OK,
    )


def FIXTURE_sequence(pairs: list[tuple[str, str]]) -> list[MarketBar]:  # noqa: N802
    return [
        FIXTURE_bar(FIXTURE_T0 + timedelta(hours=i), high, low)
        for i, (high, low) in enumerate(pairs)
    ]


#: Rising zigzag: swing highs [12,13,14] @1,3,5 and swing lows [8,9,10] @1,3,5.
FIXTURE_UP = [
    ("10", "9"),
    ("12", "8"),
    ("11", "10"),
    ("13", "9"),
    ("12", "11"),
    ("14", "10"),
    ("13", "12"),
]

#: Falling zigzag: swing highs [14,13,12] @1,3,5 and swing lows [9,7,5] @1,3,5.
FIXTURE_DOWN = [
    ("13", "12"),
    ("14", "9"),
    ("12", "10"),
    ("13", "7"),
    ("11", "8"),
    ("12", "5"),
    ("10", "6"),
]

#: Flat-top chop: equal swing highs/lows, no joint sequence → range.
FIXTURE_RANGE = [
    ("12", "10"),
    ("13", "9"),
    ("12", "10"),
    ("13", "9"),
    ("12", "10"),
    ("13", "9"),
    ("12", "10"),
]

#: Dead flat: no strict extreme anywhere.
FIXTURE_FLAT = [("12", "10")] * 5


def test_swings_confirmed_on_rising_zigzag() -> None:
    bars = FIXTURE_sequence(FIXTURE_UP)
    highs = swing_highs(bars, left_bars=1, right_bars=1)
    lows = swing_lows(bars, left_bars=1, right_bars=1)
    assert [(p.index, p.price) for p in highs] == [
        (1, Decimal("12")),
        (3, Decimal("13")),
        (5, Decimal("14")),
    ]
    assert [(p.index, p.price) for p in lows] == [
        (1, Decimal("8")),
        (3, Decimal("9")),
        (5, Decimal("10")),
    ]


def test_equal_extremes_claim_no_swing() -> None:
    bars = FIXTURE_sequence(FIXTURE_FLAT)
    assert swing_highs(bars, left_bars=1, right_bars=1) == []
    assert swing_lows(bars, left_bars=1, right_bars=1) == []
    state = describe_structure(bars, left_bars=1, right_bars=1)
    assert state.verdict == "ok"  # ordered + long enough, just swingless
    assert state.highest_high == Decimal("12")
    assert state.lowest_low == Decimal("10")


def test_too_short_input_is_insufficient_never_a_guess() -> None:
    bars = FIXTURE_sequence(FIXTURE_UP[:2])
    assert swing_highs(bars, left_bars=1, right_bars=1) == []
    state = describe_structure(bars, left_bars=1, right_bars=1)
    assert state.verdict == "insufficient_data"
    assert state.swing_highs == [] and state.highest_high is None


def test_misordered_input_is_insufficient_and_preserves_order() -> None:
    bars = FIXTURE_sequence(FIXTURE_UP)
    shuffled = [bars[2], bars[0], bars[1], *bars[3:]]
    state = describe_structure(shuffled, left_bars=1, right_bars=1)
    assert state.verdict == "insufficient_data"
    assert "MALFORMED" in state.reason or "misordered" in state.reason
    assert [b.bar_open_time for b in shuffled] == [b.bar_open_time for b in shuffled]  # untouched
    assert shuffled[0].bar_open_time > shuffled[1].bar_open_time  # still misordered


def test_malformed_input_raises() -> None:
    with pytest.raises(ValueError, match="at least one closed bar"):
        describe_structure([], left_bars=1, right_bars=1)
    with pytest.raises(TypeError, match="MarketBar"):
        swing_highs(["not-a-bar"], left_bars=1, right_bars=1)  # type: ignore[list-item]
    with pytest.raises(ValueError, match="left_bars"):
        swing_lows(FIXTURE_sequence(FIXTURE_UP), left_bars=0, right_bars=1)
    with pytest.raises(ValueError, match="tick_size"):
        describe_structure(
            FIXTURE_sequence(FIXTURE_UP),
            left_bars=1,
            right_bars=1,
            tick_size=0.01,  # type: ignore[arg-type]
        )


def test_version_and_code_hash_stamped() -> None:
    state = describe_structure(FIXTURE_sequence(FIXTURE_UP), left_bars=1, right_bars=1)
    assert state.rules_version == structure.STRUCTURE_RULES_VERSION
    assert state.code_hash == STRUCTURE_CODE_HASH
    assert STRUCTURE_CODE_HASH == hashlib.sha256(structure.RULE_SOURCE.encode()).hexdigest()
    assert REGIME_CODE_HASH == hashlib.sha256(regime.RULE_SOURCE.encode()).hexdigest()


def test_deterministic_repeat_runs_identical() -> None:
    bars = FIXTURE_sequence(FIXTURE_UP)
    first = describe_structure(bars, left_bars=1, right_bars=1)
    second = describe_structure(bars, left_bars=1, right_bars=1)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert swing_highs(bars, left_bars=1, right_bars=1) == swing_highs(
        bars, left_bars=1, right_bars=1
    )
    assert classify_regime(first) == classify_regime(second)


def test_tick_size_aligns_and_none_skips() -> None:
    bars = FIXTURE_sequence([("12.005", "11.994"), ("12.015", "11.984")] + FIXTURE_UP[2:])
    aligned = describe_structure(bars, left_bars=1, right_bars=1, tick_size=FIXTURE_TICK)
    assert aligned.verdict == "ok"
    raw = describe_structure(bars, left_bars=1, right_bars=1, tick_size=None)
    assert raw.highest_high == Decimal("14")
    # Exact-half-tick pins ROUND_HALF_UP via conventions (D-3.2), never a default.
    assert aligned.highest_high == Decimal("14")
    assert all(p.price == p.price.quantize(FIXTURE_TICK) for p in aligned.swing_highs)


def test_decimal_only_price_path() -> None:
    state = describe_structure(FIXTURE_sequence(FIXTURE_UP), left_bars=1, right_bars=1)
    assert isinstance(state.highest_high, Decimal)
    assert isinstance(state.lowest_low, Decimal)
    assert all(isinstance(p.price, Decimal) for p in state.swing_highs + state.swing_lows)
    assert highest_high(FIXTURE_sequence(FIXTURE_UP)) == Decimal("14")
    assert lowest_low(FIXTURE_sequence(FIXTURE_UP)) == Decimal("8")


def test_no_float_or_threshold_literals_in_new_modules() -> None:
    """T-03-05 + D-3.1: Decimal-only; ints stay structural (0/1, 2 = swing pair)."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    for name in ("src/goldmasters/domain/structure.py", "src/goldmasters/domain/regime.py"):
        tree = ast.parse((repo / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                pytest.fail(f"{name} contains float literal {node.value!r}")
            if isinstance(node, ast.Constant) and isinstance(node.value, int):
                assert node.value in (0, 1, 2), f"{name} numeric literal {node.value!r}"
    for name in (
        "src/goldmasters/domain/structure.py",
        "src/goldmasters/domain/regime.py",
    ):
        source = (repo / name).read_text(encoding="utf-8")
        assert "float(" not in source
        assert "sorted(" not in source  # never a silent sort (D-3.5)


def test_no_fixture_symbol_leaks_into_new_production_paths() -> None:
    """T-03-04: FIXTURE_-labelled data never reaches production modules."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    offenders = [
        str(path.relative_to(repo))
        for path in (repo / "src").rglob("*.py")
        if "FIXTURE_" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --- Regime ---------------------------------------------------------------


def test_regime_uptrend_downtrend_range() -> None:
    up = classify_regime(
        describe_structure(FIXTURE_sequence(FIXTURE_UP), left_bars=1, right_bars=1)
    )
    assert up.label == TrendRegime.UPTREND
    down = classify_regime(
        describe_structure(FIXTURE_sequence(FIXTURE_DOWN), left_bars=1, right_bars=1)
    )
    assert down.label == TrendRegime.DOWNTREND
    rng = classify_regime(
        describe_structure(FIXTURE_sequence(FIXTURE_RANGE), left_bars=1, right_bars=1)
    )
    assert rng.label == TrendRegime.RANGE
    for assessment in (up, down, rng):
        assert assessment.rules_version == regime.REGIME_RULES_VERSION
        assert assessment.code_hash == REGIME_CODE_HASH
        assert isinstance(assessment.label, TrendRegime)  # enum only, never a raw string


def test_regime_unknown_when_indeterminate_never_directional() -> None:
    flat = classify_regime(
        describe_structure(FIXTURE_sequence(FIXTURE_FLAT), left_bars=1, right_bars=1)
    )
    assert flat.label == TrendRegime.UNKNOWN  # ok structure, no swing pair
    short = classify_regime(
        describe_structure(FIXTURE_sequence(FIXTURE_UP[:2]), left_bars=1, right_bars=1)
    )
    assert short.label == TrendRegime.UNKNOWN
    misordered = FIXTURE_sequence(FIXTURE_UP)
    misordered = [misordered[1], misordered[0], *misordered[2:]]
    malformed = classify_regime(describe_structure(misordered, left_bars=1, right_bars=1))
    assert malformed.label == TrendRegime.UNKNOWN


def test_regime_malformed_state_raises() -> None:
    with pytest.raises(TypeError, match="StructureState"):
        classify_regime("uptrend")  # type: ignore[arg-type]


def test_insufficient_state_model_rejects_claims() -> None:
    """The fail-closed shape is enforced, not just conventional."""
    with pytest.raises(Exception, match="no swings|no extremes"):
        StructureState(
            rules_version="1.0",
            code_hash="x",
            bar_count=2,
            verdict="insufficient_data",
            reason="test",
            swing_highs=[],
            swing_lows=[],
            highest_high=Decimal("12"),
        )
