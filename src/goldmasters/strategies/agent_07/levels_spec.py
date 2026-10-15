"""Agent 7 levels mapping: rule-derived prices to level-builder arguments.

Agents never construct levels directly; this module maps the rule-derived
entry/stop/target to ``build_candidate_levels`` arguments. The target is the
rule-derived reference price (the basis the deviation is expected to
partially reverse toward) — derived arithmetic, no threshold literal.
"""

from __future__ import annotations

from decimal import Decimal

from goldmasters_contracts import Direction


def take_profits_for(*, direction: Direction, entry: Decimal, target: Decimal) -> list[Decimal]:
    """Reference-price target on the reversion side of entry."""
    if direction == Direction.LONG:
        assert target > entry, "reversion target must sit above a long entry"
    else:
        assert target < entry, "reversion target must sit below a short entry"
    return [target]
