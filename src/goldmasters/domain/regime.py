"""Trend/regime classification: versioned rules, labels ONLY from TrendRegime (D-3.1).

Ordinal comparisons over :class:`StructureState` swings — no numeric
thresholds, so no settings argument is needed and none is accepted. Any
indeterminate input (insufficient structure, fewer than a swing pair per
side) yields ``TrendRegime.UNKNOWN``, which downstream means no setup
(03-CONTEXT.md architecture). Unknown is never a directional guess.
"""

from __future__ import annotations

from goldmasters_contracts import ContractModel, TrendRegime

from src.goldmasters.domain.structure import (
    STRUCTURE_RULES_VERSION,
    StructureState,
    hash_rule_source,
)

__all__ = [
    "REGIME_CODE_HASH",
    "REGIME_RULES_VERSION",
    "RULE_SOURCE",
    "RegimeAssessment",
    "classify_regime",
]

#: Semver of the classification rules below; bumped on any rule change.
REGIME_RULES_VERSION = "1.0"

#: The rule text the integrity label covers (stable literal, see structure.py).
RULE_SOURCE = (
    f"regime/1.0 over structure/{STRUCTURE_RULES_VERSION}: insufficient structure is unknown; "
    "fewer than a swing pair per side is unknown; last-two-highs rising with "
    "last-two-lows rising is uptrend; both falling is downtrend; any other "
    "confirmed-swing shape is range"
)


def _rule_hash() -> str:
    return hash_rule_source(RULE_SOURCE)


#: Integrity label stamped on every output of this module.
REGIME_CODE_HASH = _rule_hash()


class RegimeAssessment(ContractModel):
    """One versioned regime label with the evidence that produced it."""

    label: TrendRegime
    rules_version: str
    code_hash: str
    reason: str
    evidence: str


def _unknown(reason: str, evidence: str) -> RegimeAssessment:
    return RegimeAssessment(
        label=TrendRegime.UNKNOWN,
        rules_version=REGIME_RULES_VERSION,
        code_hash=REGIME_CODE_HASH,
        reason=reason,
        evidence=evidence,
    )


def classify_regime(state: StructureState) -> RegimeAssessment:
    """Classify confirmed structure into a TrendRegime label, fail-closed.

    A directional label needs a swing *pair* per side (a comparison needs two
    points — structural, not a policy threshold); anything less is
    ``UNKNOWN``. Labels come ONLY from the ``TrendRegime`` enum.
    """
    if not isinstance(state, StructureState):
        raise TypeError("state must be StructureState (malformed input raises)")
    if state.verdict != "ok":
        return _unknown(
            "structure insufficient: no regime claimed",
            f"structure verdict={state.verdict} reason={state.reason}",
        )
    highs = state.swing_highs
    lows = state.swing_lows
    # A pair per side is the minimum a higher-high / lower-low claim needs
    # (2 is pair-structure, not a policy threshold: a comparison needs two points).
    if len(highs) < 2 or len(lows) < 2:
        return _unknown(
            "fewer than a swing pair per side: indeterminate, never directional",
            f"swing_highs={len(highs)} swing_lows={len(lows)} bars={state.bar_count}",
        )
    highs_rising = highs[-1].price > highs[-2].price
    lows_rising = lows[-1].price > lows[-2].price
    highs_falling = highs[-1].price < highs[-2].price
    lows_falling = lows[-1].price < lows[-2].price
    evidence = (
        f"highs[-2:]={[str(p.price) for p in highs[-2:]]} "
        f"lows[-2:]={[str(p.price) for p in lows[-2:]]} bars={state.bar_count}"
    )
    if highs_rising and lows_rising:
        return RegimeAssessment(
            label=TrendRegime.UPTREND,
            rules_version=REGIME_RULES_VERSION,
            code_hash=REGIME_CODE_HASH,
            reason="last-two swing highs and lows both rising",
            evidence=evidence,
        )
    if highs_falling and lows_falling:
        return RegimeAssessment(
            label=TrendRegime.DOWNTREND,
            rules_version=REGIME_RULES_VERSION,
            code_hash=REGIME_CODE_HASH,
            reason="last-two swing highs and lows both falling",
            evidence=evidence,
        )
    return RegimeAssessment(
        label=TrendRegime.RANGE,
        rules_version=REGIME_RULES_VERSION,
        code_hash=REGIME_CODE_HASH,
        reason="confirmed swings without a joint higher/lower sequence",
        evidence=evidence,
    )
