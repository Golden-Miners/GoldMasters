"""Agent 1 levels mapping: rule-derived prices to level-builder arguments.

Agents never construct levels directly; this module maps the rule-derived
entry/stop to ``build_candidate_levels`` arguments. The single target is the
one-risk projection of the structural stop distance — derived arithmetic, no
threshold literal.
"""

from __future__ import annotations

from decimal import Decimal

from goldmasters_contracts import Direction


def take_profits_for(
    *, direction: Direction, entry: Decimal, stop: Decimal
) -> list[Decimal]:
    """One-risk target above entry (long) or below it (short)."""
    if direction == Direction.LONG:
        return [entry + (entry - stop)]
    return [entry - (stop - entry)]
