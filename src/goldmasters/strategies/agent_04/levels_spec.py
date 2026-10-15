"""Agent 4 levels mapping: rule-derived prices to level-builder arguments.

The stop is the structural swing extreme (failure handling); the target is
the one-risk projection — derived arithmetic, no threshold literal.
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
