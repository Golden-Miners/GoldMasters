"""Agent 2 levels mapping: rule-derived prices to level-builder arguments.

Same contract as Agent 1: entry/stop flow to ``build_candidate_levels`` with
a one-risk derived target — code computes, never a threshold literal.
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
