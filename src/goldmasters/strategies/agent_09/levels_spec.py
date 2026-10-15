"""Agent 9 levels mapping: rule-derived prices to level-builder arguments.

Agents never construct levels directly; this module maps the rule-derived
entry/stop/target to ``build_candidate_levels`` arguments. The stop sits
beyond the sweep extreme (invalidation on acceptance past the pool); the
target is the opposing pre-sweep extreme (the next resting liquidity) —
derived arithmetic, no threshold literal.
"""

from __future__ import annotations

from decimal import Decimal

from goldmasters_contracts import Direction


def take_profits_for(*, direction: Direction, entry: Decimal, target: Decimal) -> list[Decimal]:
    """Opposing-pool target on the setup side of entry."""
    if direction == Direction.LONG:
        assert target > entry, "opposing-pool target must sit above a long entry"
    else:
        assert target < entry, "opposing-pool target must sit below a short entry"
    return [target]
