"""Levels contract (03-03 Task 1): code-computed, quantized, ordered, null-unknown.

All prices are ``Decimal`` literals in fixtures (test-only, never production
data — Rules §9.7). No threshold literal appears: the tick size is an explicit
``Decimal`` argument standing in for the precision-table value.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from goldmasters_contracts import Direction

from src.goldmasters.risk.levels import (
    build_candidate_levels,
    compute_risk_reward,
    validate_level_ordering,
)
from src.goldmasters.strategies.base import RuleCheck

TICK = Decimal("0.01")


def _pass_checks() -> list[RuleCheck]:
    return [RuleCheck(rule_id="rule-1", verdict="pass", evidence="e", reason="r")]


def _fail_checks() -> list[RuleCheck]:
    return [RuleCheck(rule_id="rule-1", verdict="fail", evidence="e", reason="r")]


def test_long_ordering_passes_and_quantizes() -> None:
    levels = build_candidate_levels(
        direction=Direction.LONG,
        rule_checks=_pass_checks(),
        entry=Decimal("100.005"),
        stop_loss=Decimal("99.00"),
        take_profits=[Decimal("101.00"), Decimal("102.00")],
        tick_size=TICK,
    )
    assert levels is not None
    assert levels.entry == Decimal("100.01")  # exact-half-tick rounds half-up (D-3.2)
    assert levels.stop_loss == Decimal("99.00")
    assert levels.take_profits == [Decimal("101.00"), Decimal("102.00")]
    assert levels.risk_reward == (Decimal("101.00") - Decimal("100.01")) / (
        Decimal("100.01") - Decimal("99.00")
    )


def test_short_mirror_ordering_passes() -> None:
    levels = build_candidate_levels(
        direction=Direction.SHORT,
        rule_checks=_pass_checks(),
        entry=Decimal("100.00"),
        stop_loss=Decimal("101.00"),
        take_profits=[Decimal("99.00"), Decimal("98.00")],
        tick_size=TICK,
    )
    assert levels is not None
    assert levels.risk_reward == Decimal("1")


def test_each_misordering_direction_fails_to_null() -> None:
    cases = [
        # stop on the wrong side of entry
        (Direction.LONG, Decimal("99.00"), Decimal("100.00"), [Decimal("101.00")]),
        (Direction.SHORT, Decimal("101.00"), Decimal("100.00"), [Decimal("99.00")]),
        # targets unordered / on the wrong side
        (Direction.LONG, Decimal("100.00"), Decimal("99.00"), [Decimal("99.50")]),
        (Direction.SHORT, Decimal("100.00"), Decimal("101.00"), [Decimal("100.50")]),
        # tp2 not beyond tp1
        (
            Direction.LONG,
            Decimal("100.00"),
            Decimal("99.00"),
            [Decimal("101.00"), Decimal("100.50")],
        ),
        (
            Direction.SHORT,
            Decimal("100.00"),
            Decimal("101.00"),
            [Decimal("99.00"), Decimal("99.50")],
        ),
        # empty targets
        (Direction.LONG, Decimal("100.00"), Decimal("99.00"), []),
    ]
    for direction, entry, stop, targets in cases:
        assert (
            build_candidate_levels(
                direction=direction,
                rule_checks=_pass_checks(),
                entry=entry,
                stop_loss=stop,
                take_profits=[Decimal(str(t)) for t in targets],
                tick_size=TICK,
            )
            is None
        )


def test_unknown_direction_stays_null() -> None:
    for direction in (Direction.NEUTRAL, Direction.UNKNOWN):
        assert (
            build_candidate_levels(
                direction=direction,
                rule_checks=_pass_checks(),
                entry=Decimal("100.00"),
                stop_loss=Decimal("99.00"),
                take_profits=[Decimal("101.00")],
                tick_size=TICK,
            )
            is None
        )


def test_failed_rule_check_stays_null() -> None:
    assert (
        build_candidate_levels(
            direction=Direction.LONG,
            rule_checks=_fail_checks(),
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.00"),
            take_profits=[Decimal("101.00")],
            tick_size=TICK,
        )
        is None
    )


def test_claimed_risk_reward_mismatch_blocks() -> None:
    """T-03-08: risk_reward is recomputed, never trusted from strategy output."""
    assert (
        build_candidate_levels(
            direction=Direction.LONG,
            rule_checks=_pass_checks(),
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.00"),
            take_profits=[Decimal("102.00")],
            tick_size=TICK,
            claimed_risk_reward=Decimal("999"),
        )
        is None
    )
    matching = compute_risk_reward(
        entry=Decimal("100.00"), stop_loss=Decimal("99.00"), first_target=Decimal("102.00")
    )
    assert (
        build_candidate_levels(
            direction=Direction.LONG,
            rule_checks=_pass_checks(),
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.00"),
            take_profits=[Decimal("102.00")],
            tick_size=TICK,
            claimed_risk_reward=matching,
        )
        is not None
    )


def test_compute_risk_reward_rejects_zero_distance() -> None:
    with pytest.raises(ValueError, match="non-positive"):
        compute_risk_reward(
            entry=Decimal("100.00"), stop_loss=Decimal("100.00"), first_target=Decimal("101.00")
        )


def test_non_decimal_tick_rejected() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        build_candidate_levels(
            direction=Direction.LONG,
            rule_checks=_pass_checks(),
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.00"),
            take_profits=[Decimal("101.00")],
            tick_size=0.01,  # type: ignore[arg-type]
        )


def test_ordering_validated_on_quantized_values() -> None:
    """A pair that orders pre-quantization but collides on the grid stays null."""
    assert (
        validate_level_ordering(
            direction=Direction.LONG,
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.996"),
            take_profits=[Decimal("101.00")],
        )
        == []
    )
    assert (
        build_candidate_levels(
            direction=Direction.LONG,
            rule_checks=_pass_checks(),
            entry=Decimal("100.00"),
            stop_loss=Decimal("99.996"),  # quantizes to 100.00 == entry
            take_profits=[Decimal("101.00")],
            tick_size=TICK,
        )
        is None
    )
