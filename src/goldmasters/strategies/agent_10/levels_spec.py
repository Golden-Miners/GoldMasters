"""Agent 10 levels mapping: no rule-derived prices exist yet.

Agents never construct levels directly; this module maps rule-derived
entry/stop/target to ``build_candidate_levels`` arguments. Carry legs ship
NOT_APPLICABLE-first (source adapters are Phase 6+/operator-supplied), so
there are no rule-derived prices to map — calling this before a leg passes
is a composition bug, reported loudly rather than defaulted.
"""

from __future__ import annotations

from decimal import Decimal

from goldmasters_contracts import Direction


def take_profits_for(*, direction: Direction, entry: Decimal, target: Decimal) -> list[Decimal]:
    """No carry leg passes yet: raising beats emitting an uninferred level."""
    raise AssertionError(
        "carry-term-structure emits no levels: legs NOT_APPLICABLE-first "
        f"({direction} {entry}/{target} has no verified carry source)"
    )
